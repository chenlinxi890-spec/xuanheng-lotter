import io
import pandas as pd
from .games import GAMES, validate_record

def parse_csv(game, content):
    df = pd.read_csv(io.BytesIO(content), dtype=str).fillna("")
    required = ["issue"] + [f["key"] for f in GAMES[game]["fields"]]
    missing = [x for x in required if x not in df.columns]
    if missing:
        raise ValueError("CSV缺少列：" + ", ".join(missing))
    out = []
    for _, row in df.iterrows():
        out.append(validate_record(game, {k: row[k] for k in required}))
    if not out:
        raise ValueError("CSV没有数据行")
    return out

def export_records(game, records):
    return pd.DataFrame(records).to_csv(index=False).encode("utf-8-sig")
