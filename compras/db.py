"""Persistência em SQLite.

- item:    o que a casa precisa, genérico ("Arroz", medido em kg)
- produto: um SKU concreto numa loja ("Arroz Qualitá Tipo 1 5kg" no Pão de Açúcar)
- preco:   histórico de preços de cada produto
- lista:   lista de compras atual (item + quantidade necessária)
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from compras import ErroCompras
from compras.texto import normalizar

SCHEMA = """
CREATE TABLE IF NOT EXISTS itens (
    id        INTEGER PRIMARY KEY,
    nome      TEXT NOT NULL,
    chave     TEXT NOT NULL UNIQUE,
    unidade   TEXT NOT NULL CHECK (unidade IN ('kg', 'L', 'un')),
    categoria TEXT
);

CREATE TABLE IF NOT EXISTS produtos (
    id         INTEGER PRIMARY KEY,
    item_id    INTEGER NOT NULL REFERENCES itens(id) ON DELETE CASCADE,
    loja_id    TEXT NOT NULL,
    descricao  TEXT NOT NULL COLLATE NOCASE,
    marca      TEXT,
    quantidade REAL NOT NULL CHECK (quantidade > 0),  -- na unidade do item
    url        TEXT,
    UNIQUE (loja_id, descricao)
);

CREATE TABLE IF NOT EXISTS precos (
    id         INTEGER PRIMARY KEY,
    produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    preco      REAL NOT NULL CHECK (preco > 0),
    promocao   INTEGER NOT NULL DEFAULT 0,
    data       TEXT NOT NULL,
    fonte      TEXT NOT NULL DEFAULT 'manual'
);
CREATE INDEX IF NOT EXISTS idx_precos_produto ON precos (produto_id, data);

CREATE TABLE IF NOT EXISTS lista (
    item_id    INTEGER PRIMARY KEY REFERENCES itens(id) ON DELETE CASCADE,
    quantidade REAL  -- NULL = "uma embalagem, a de melhor custo-benefício"
);
"""


def conectar(caminho: Path | str) -> sqlite3.Connection:
    if str(caminho) != ":memory:":
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


# --- itens ---------------------------------------------------------------

def criar_item(conn: sqlite3.Connection, nome: str, unidade: str, categoria: str | None = None) -> int:
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO itens (nome, chave, unidade, categoria) VALUES (?, ?, ?, ?)",
                (nome.strip(), normalizar(nome), unidade, categoria),
            )
    except sqlite3.IntegrityError:
        raise ErroCompras(f"Item {nome!r} já existe") from None
    return cur.lastrowid


def buscar_item(conn: sqlite3.Connection, nome: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM itens WHERE chave = ?", (normalizar(nome),)).fetchone()
    if row is None:
        raise ErroCompras(f"Item {nome!r} não cadastrado. Use: compras item add {nome!r} --unidade kg")
    return row


def listar_itens(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM itens ORDER BY categoria, nome").fetchall()


def remover_item(conn: sqlite3.Connection, item_id: int) -> None:
    with conn:
        conn.execute("DELETE FROM itens WHERE id = ?", (item_id,))


# --- produtos e preços ---------------------------------------------------

def salvar_produto(
    conn: sqlite3.Connection,
    item_id: int,
    loja_id: str,
    descricao: str,
    quantidade: float,
    marca: str | None = None,
    url: str | None = None,
) -> int:
    with conn:
        return conn.execute(
            """
            INSERT INTO produtos (item_id, loja_id, descricao, marca, quantidade, url)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (loja_id, descricao) DO UPDATE SET
                item_id = excluded.item_id,
                quantidade = excluded.quantidade,
                marca = COALESCE(excluded.marca, marca),
                url = COALESCE(excluded.url, url)
            RETURNING id
            """,
            (item_id, loja_id, descricao.strip(), marca, quantidade, url),
        ).fetchone()[0]


def registrar_preco(
    conn: sqlite3.Connection,
    produto_id: int,
    preco: float,
    data: date | None = None,
    promocao: bool = False,
    fonte: str = "manual",
) -> None:
    with conn:
        conn.execute(
            "INSERT INTO precos (produto_id, preco, promocao, data, fonte) VALUES (?, ?, ?, ?, ?)",
            (produto_id, preco, int(promocao), (data or date.today()).isoformat(), fonte),
        )


def produtos_do_item(conn: sqlite3.Connection, item_id: int, loja_id: str | None = None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM produtos WHERE item_id = ?"
    args: tuple = (item_id,)
    if loja_id:
        sql += " AND loja_id = ?"
        args += (loja_id,)
    return conn.execute(sql + " ORDER BY loja_id, descricao", args).fetchall()


def historico(conn: sqlite3.Connection, produto_id: int) -> list[sqlite3.Row]:
    """Preços do produto, do mais antigo ao mais recente."""
    return conn.execute(
        "SELECT * FROM precos WHERE produto_id = ? ORDER BY data, id", (produto_id,)
    ).fetchall()


# --- lista de compras ----------------------------------------------------

def lista_definir(conn: sqlite3.Connection, item_id: int, quantidade: float | None) -> None:
    with conn:
        conn.execute(
            "INSERT INTO lista (item_id, quantidade) VALUES (?, ?) "
            "ON CONFLICT (item_id) DO UPDATE SET quantidade = excluded.quantidade",
            (item_id, quantidade),
        )


def lista_remover(conn: sqlite3.Connection, item_id: int) -> None:
    with conn:
        conn.execute("DELETE FROM lista WHERE item_id = ?", (item_id,))


def lista_limpar(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute("DELETE FROM lista")


def lista_itens(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT i.*, l.quantidade AS necessidade FROM lista l JOIN itens i ON i.id = l.item_id "
        "ORDER BY i.categoria, i.nome"
    ).fetchall()
