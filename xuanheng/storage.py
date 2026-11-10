import sqlite3, json
from pathlib import Path
from .games import validate_record

DB = Path(__file__).resolve().parents[1] / "data" / "xuanheng.db"

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS draws (
            game TEXT NOT NULL, issue TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(game, issue))""")

def upsert_records(game, records):
    with connect() as c:
        for r in records:
            clean = validate_record(game, r)
            c.execute("INSERT INTO draws(game,issue,payload) VALUES(?,?,?) "
                      "ON CONFLICT(game,issue) DO UPDATE SET payload=excluded.payload",
                      (game, clean["issue"], json.dumps(clean, ensure_ascii=False)))

def load_records(game):
    with connect() as c:
        rows = c.execute("SELECT payload FROM draws WHERE game=?", (game,)).fetchall()
    data = [json.loads(x["payload"]) for x in rows]
    return sorted(data, key=lambda x: x["issue"], reverse=True)

def count_records(game):
    with connect() as c:
        return c.execute("SELECT COUNT(*) FROM draws WHERE game=?", (game,)).fetchone()[0]

def clear_game(game):
    with connect() as c:
        c.execute("DELETE FROM draws WHERE game=?", (game,))
