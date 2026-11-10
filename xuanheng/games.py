GAMES = {
    "pl3": {"name": "排列三", "fields": [
        {"key":"d1","label":"百位","min":0,"max":9,"count":1},
        {"key":"d2","label":"十位","min":0,"max":9,"count":1},
        {"key":"d3","label":"个位","min":0,"max":9,"count":1}]},
    "pl5": {"name": "排列五", "fields": [
        {"key":f"d{i}","label":f"第{i}位","min":0,"max":9,"count":1} for i in range(1,6)]},
    "dlt": {"name": "大乐透", "fields": [
        {"key":"front","label":"前区","min":1,"max":35,"count":5},
        {"key":"back","label":"后区","min":1,"max":12,"count":2}]},
    "ssq": {"name": "双色球", "fields": [
        {"key":"red","label":"红球","min":1,"max":33,"count":6},
        {"key":"blue","label":"蓝球","min":1,"max":16,"count":1}]},
    "qxc": {"name": "七星彩", "fields": [
        {"key":f"d{i}","label":f"第{i}位","min":0,"max":9,"count":1} for i in range(1,8)]}
}

def template_columns(game):
    import pandas as pd
    keys = ["issue"] + [f["key"] for f in GAMES[game]["fields"]]
    return pd.DataFrame(columns=keys)

def validate_record(game, record):
    spec = GAMES[game]
    if not str(record.get("issue","")).strip():
        raise ValueError("期号不能为空")
    clean = {"issue": str(record["issue"]).strip()}
    for f in spec["fields"]:
        raw = record.get(f["key"])
        if f["count"] == 1:
            vals = [int(raw)]
        else:
            vals = [int(x) for x in str(raw).replace(",", " ").split()]
        if len(vals) != f["count"]:
            raise ValueError(f"{f['label']}应有 {f['count']} 个号码")
        if any(x < f["min"] or x > f["max"] for x in vals):
            raise ValueError(f"{f['label']}号码范围应为 {f['min']}–{f['max']}")
        if len(set(vals)) != len(vals):
            raise ValueError(f"{f['label']}存在重复号码")
        if f["count"] > 1:
            vals.sort()
            clean[f["key"]] = " ".join(f"{x:02d}" for x in vals)
        else:
            clean[f["key"]] = f"{vals[0]:02d}" if f["min"] == 0 else str(vals[0])
    return clean
