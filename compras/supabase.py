"""Cliente mínimo da API REST (PostgREST) do Supabase, usando a chave de serviço."""

from __future__ import annotations

import os
from pathlib import Path

import httpx

LOTE = 500  # linhas por requisição de escrita
PAGINA = 1000  # limite padrão de linhas por leitura no Supabase


def _env(nome: str) -> str:
    if nome in os.environ:
        return os.environ[nome]
    arquivo = Path(__file__).resolve().parents[1] / ".env"
    if arquivo.is_file():
        for linha in arquivo.read_text().splitlines():
            if linha.startswith(nome + "="):
                return linha.split("=", 1)[1].strip()
    raise RuntimeError(f"Variável {nome} não definida (nem no ambiente, nem no .env)")


class Supabase:
    def __init__(self, url: str | None = None, chave: str | None = None):
        url = url or _env("SUPABASE_URL")
        chave = chave or _env("SUPABASE_SERVICE_ROLE_KEY")
        self.http = httpx.Client(
            base_url=f"{url}/rest/v1",
            headers={"apikey": chave, "Authorization": f"Bearer {chave}"},
            timeout=60,
        )

    def _checar(self, r: httpx.Response) -> httpx.Response:
        if r.is_error:
            raise RuntimeError(f"Supabase {r.status_code} em {r.request.method} {r.request.url.path}: {r.text}")
        return r

    def select(self, tabela: str, colunas: str = "*", ordem: str | None = None, **filtros: str) -> list[dict]:
        """Lê todas as linhas que batem com os filtros (ex.: loja_id='eq.guanabara'), paginando.

        Em tabelas grandes, passe `ordem` (uma coluna única) para a paginação ser estável.
        """
        linhas, inicio = [], 0
        while True:
            r = self._checar(
                self.http.get(
                    f"/{tabela}",
                    params={"select": colunas, **({"order": ordem} if ordem else {}), **filtros},
                    headers={"Range": f"{inicio}-{inicio + PAGINA - 1}"},
                )
            )
            pagina = r.json()
            linhas += pagina
            if len(pagina) < PAGINA:
                return linhas
            inicio += PAGINA

    def upsert(self, tabela: str, linhas: list[dict], conflito: str, retornar: str | None = None) -> list[dict]:
        """Insere ou atualiza pelas colunas de `conflito`. `retornar` = colunas a devolver."""
        saida = []
        for i in range(0, len(linhas), LOTE):
            params = {"on_conflict": conflito}
            if retornar:
                params["select"] = retornar
            r = self._checar(
                self.http.post(
                    f"/{tabela}",
                    params=params,
                    json=linhas[i : i + LOTE],
                    headers={
                        "Prefer": "resolution=merge-duplicates,"
                        + ("return=representation" if retornar else "return=minimal")
                    },
                )
            )
            if retornar:
                saida += r.json()
        return saida

    def insert(self, tabela: str, linhas: list[dict], retornar: str | None = None) -> list[dict]:
        saida = []
        for i in range(0, len(linhas), LOTE):
            r = self._checar(
                self.http.post(
                    f"/{tabela}",
                    params={"select": retornar} if retornar else None,
                    json=linhas[i : i + LOTE],
                    headers={"Prefer": "return=representation" if retornar else "return=minimal"},
                )
            )
            if retornar:
                saida += r.json()
        return saida

    def update(self, tabela: str, dados: dict, **filtros: str) -> None:
        self._checar(self.http.patch(f"/{tabela}", params=filtros, json=dados, headers={"Prefer": "return=minimal"}))
