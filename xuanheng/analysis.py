import math
from collections import Counter
from itertools import product
from .games import GAMES

def _numbers(game, record, field):
    spec = next(x for x in GAMES[game]["fields"] if x["key"] == field["key"])
    raw = record[field["key"]]
    return [int(x) for x in raw.split()] if spec["count"] > 1 else [int(raw)]

def _all_position_values(game, records, field):
    vals = []
    for r in records:
        vals.extend(_numbers(game, r, field))
    return vals

def analyze_game(game, records, window=100):
    recent = records[:window]
    freq, omissions = {}, {}
    for f in GAMES[game]["fields"]:
        vals = _all_position_values(game, recent, f)
        c = Counter(vals)
        freq[f["label"]] = {str(i): c.get(i,0) for i in range(f["min"], f["max"]+1)}
        # omission is distance from newest draw to most recent appearance
        full = _all_position_values(game, records, f)
        for i in range(f["min"], f["max"]+1):
            omissions.setdefault(f["label"], {})[str(i)] = next((idx for idx,v in enumerate(full) if v == i), len(full))
    structure = {}
    if game in ("pl3","pl5","qxc"):
        draws = [[int(r[f["key"]]) for f in GAMES[game]["fields"]] for r in recent]
        if draws:
            sums = [sum(x) for x in draws]
            spans = [max(x)-min(x) for x in draws]
            structure = {
                "平均和值": round(sum(sums)/len(sums),2),
                "平均跨度": round(sum(spans)/len(spans),2),
                "最近一期和值": sums[0],
                "最近一期跨度": spans[0],
                "最近一期奇偶": "".join("奇" if x%2 else "偶" for x in draws[0]),
                "最近一期大小": "".join("大" if x>=5 else "小" for x in draws[0]),
                "最近一期012路": "".join(str(x%3) for x in draws[0])
            }
    return {"position_frequency":freq, "omissions":omissions, "structure":structure, "window":len(recent)}

def build_candidate(game, records, window=100):
    if not records:
        return {"error":"没有历史数据"}
    fields = GAMES[game]["fields"]
    recent = records[:window]
    selected = {}
    explanation = []
    for f in fields:
        allowed = list(range(f["min"], f["max"]+1))
        vals = _all_position_values(game, recent, f)
        counts = Counter(vals)
        # Smoothed descriptive ranking only; frequency is not a probability forecast.
        ranked = sorted(allowed, key=lambda n:(counts.get(n,0), -n), reverse=True)
        selected[f["key"]] = ranked
        explanation.append(f"{f['label']}候选排序：{' '.join(map(str, ranked[:5]))}")
    # A single transparent line: choose top-ranked values; multi-number fields choose top count.
    result = {}
    for f in fields:
        n = f["count"]
        picks = sorted(selected[f["key"]][:n])
        result[f["key"]] = " ".join(f"{x:02d}" for x in picks) if n>1 else f"{picks[0]:02d}"
    display_parts = []
    for f in fields:
        display_parts.append(f"{f['label']} {result[f['key']]}")
    metrics = {"统计窗口":len(recent), "方法":"近期位置频数排序；并列时优先较小数字", "说明":"排序分不等于中奖概率"}
    return {"game":game,"display":" | ".join(display_parts),"fields":result,
            "explanation":"；".join(explanation), "metrics":metrics}


# ---------- 偏差检测 ----------
# 只用标准库 math，不依赖 scipy/numpy。
# 检验这段样本是否与均匀随机一致，不参与选号，不预测下一期。

def _gammln(xx):
    """ln Gamma(xx) 的 Lanczos 近似（Numerical Recipes）。"""
    cof = [76.18009172947146, -86.50532032941677, 24.01409824083091,
           -1.231739572450155, 0.001208650973866179, -0.000005395239384953]
    x = xx
    y = xx
    tmp = x + 5.5
    tmp -= (x + 0.5) * math.log(tmp)
    ser = 1.000000000190015
    for j in range(6):
        y += 1.0
        ser += cof[j] / y
    return -tmp + math.log(2.5066282746310005 * ser / x)

def _gser(a, x):
    """级数展开：正则化下不完全伽马 P(a, x)。"""
    gln = _gammln(a)
    if x <= 0.0:
        return 0.0
    ap = a
    total = 1.0 / a
    delta = total
    for _ in range(1000):
        ap += 1.0
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * 1e-14:
            break
    return total * math.exp(-x + a * math.log(x) - gln)

def _gcf(a, x):
    """连分式展开：正则化上不完全伽马 Q(a, x)。"""
    gln = _gammln(a)
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return math.exp(-x + a * math.log(x) - gln) * h

def gammq(a, x):
    """正则化上不完全伽马 Q(a, x) = Gamma(a, x) / Gamma(a)。"""
    if x < 0.0 or a <= 0.0:
        raise ValueError("gammq 参数无效：a 须大于 0，x 须大于等于 0")
    if x == 0.0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gser(a, x)
    return _gcf(a, x)

def chi_square_p(chi2, df):
    """卡方分布右尾概率 P(X >= chi2)，自由度 df。"""
    if chi2 < 0 or df < 1:
        raise ValueError("chi_square_p 参数无效")
    return gammq(df / 2.0, chi2 / 2.0)

def _normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def _runs_test(values):
    """Wald-Wolfowitz 游程检验：序列按奇/偶二值化。"""
    seq = [1 if v % 2 else 0 for v in values]
    n = len(seq)
    n1 = sum(seq)
    n0 = n - n1
    if n < 2 or n1 == 0 or n0 == 0:
        return {"runs": None, "expected": None, "z": None, "p": None,
                "note": "奇偶只有一种，游程检验不适用"}
    runs = 1 + sum(1 for i in range(1, n) if seq[i] != seq[i - 1])
    expected = 2.0 * n1 * n0 / n + 1.0
    var = (2.0 * n1 * n0 * (2.0 * n1 * n0 - n1 - n0)) / (n * n * (n - 1.0))
    if var <= 0:
        return {"runs": runs, "expected": round(expected, 2), "z": None, "p": None,
                "note": "方差为 0，无法计算 Z 值"}
    z = (runs - expected) / math.sqrt(var)
    p = 2.0 * (1.0 - _normal_cdf(abs(z)))
    return {"runs": runs, "expected": round(expected, 2), "z": round(z, 3), "p": p, "note": ""}

def bias_report(game, records, window=500):
    """偏差检测：对每个位置做卡方拟合优度检验与游程检验。

    只检验这段样本是否与均匀随机一致，不参与选号，不预测下一期。
    多位置同时检验存在多重比较问题：各位置 p 值分别报告，不合成为一个总 p 值。
    """
    if not records:
        return {"error": "没有历史数据"}
    fields = GAMES[game]["fields"]
    recent = records[:window]
    positions = []
    for f in fields:
        vals = _all_position_values(game, recent, f)
        n = len(vals)
        k = f["max"] - f["min"] + 1
        counts = Counter(vals)
        observed = {str(i): counts.get(i, 0) for i in range(f["min"], f["max"] + 1)}
        expected = n / k if k else 0.0
        if expected > 0:
            chi2 = sum((counts.get(i, 0) - expected) ** 2 / expected
                       for i in range(f["min"], f["max"] + 1))
            df = k - 1
            p = chi_square_p(chi2, df)
        else:
            chi2, df, p = 0.0, k - 1, 1.0
        runs = _runs_test(vals)
        conclusion = "偏离均匀" if p < 0.05 else "与均匀一致"
        runs_flag = ""
        if runs["p"] is not None:
            runs_flag = "游程异常" if runs["p"] < 0.05 else "游程正常"
        notes = []
        if expected < 5:
            notes.append("期望频数小于 5，卡方近似仅供参考")
        if runs["note"]:
            notes.append(runs["note"])
        positions.append({
            "label": f["label"],
            "n": n,
            "observed": observed,
            "expected": round(expected, 2),
            "chi2": round(chi2, 3),
            "df": df,
            "chi2_p": round(p, 4),
            "runs": runs["runs"],
            "runs_expected": runs["expected"],
            "runs_z": runs["z"],
            "runs_p": round(runs["p"], 4) if runs["p"] is not None else None,
            "conclusion": conclusion,
            "runs_flag": runs_flag,
            "notes": "；".join(notes),
        })
    return {
        "game": game,
        "window": len(recent),
        "positions": positions,
        "notes": [
            "卡方检验：各数字出现次数是否与均匀期望一致。",
            "游程检验：奇偶序列的游程数是否与随机排列一致。",
            "多位置同时检验存在多重比较问题：各位置 p 值分别报告，不合成为一个总 p 值；位置越多，偶然出现一个 p<0.05 的概率越高。",
            "显著偏离只说明这段样本里不均匀，不等于能预测下一期；不显著也不证明绝对均匀。",
        ],
    }
