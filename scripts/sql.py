"""Roda SQL no projeto Supabase pela Management API.

Uso: python scripts/sql.py arquivo.sql   |   python scripts/sql.py -c "select 1"
Lê SUPABASE_ACCESS_TOKEN e SUPABASE_PROJECT_REF do .env.
"""

import json
import sys
import urllib.request
from pathlib import Path


def carregar_env() -> dict:
    env = {}
    for linha in Path(__file__).resolve().parents[1].joinpath(".env").read_text().splitlines():
        if "=" in linha and not linha.startswith("#"):
            k, v = linha.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def executar(query: str) -> list:
    env = carregar_env()
    req = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{env['SUPABASE_PROJECT_REF']}/database/query",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {env['SUPABASE_ACCESS_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": "sistema-compras",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Erro {e.code}: {e.read().decode()}")


if __name__ == "__main__":
    if sys.argv[1] == "-c":
        sql = sys.argv[2]
    else:
        sql = Path(sys.argv[1]).read_text(encoding="utf-8")
    print(json.dumps(executar(sql), ensure_ascii=False, indent=1, default=str))
