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
