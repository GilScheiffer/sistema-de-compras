"""Busca no Mercado Livre pela API oficial, só anúncios do Mercado Livre Supermercado.

O site e a busca pública da API (/sites/MLB/search) bloqueiam servidores, mas o catálogo de produtos
responde com o token do app (client_credentials, secrets ML_CLIENT_ID e ML_CLIENT_SECRET).

Para cada busca: descobre as categorias prováveis, junta os mais vendidos delas (quase todos do
Supermercado) com a busca no catálogo filtrada pela categoria de mercado, e pega o anúncio mais barato do Supermercado de cada produto
(tag "supermarket_eligible"). Vendedores avulsos ficam de fora: costumam ser kits e preços inflados.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from compras.coletores import ProdutoColetado
from compras.supabase import _env

LOJA_ID = "mercado_livre"
API = "https://api.mercadolibre.com"
POR_PAGINA = 50
PAGINAS = 2
CATEGORIAS = 5
PARALELO = 8
SUPERMERCADO = "supermarket_eligible"


class Cliente:
    def __init__(self):
        self.http = httpx.Client(base_url=API, timeout=30, limits=httpx.Limits(max_connections=PARALELO))
        self._autenticar()
        self._categorias: dict[str, list[dict]] = {}
        self._dominios_mercado: set[str] = set()  # domínios onde já apareceu anúncio do Supermercado
        self._produtos: dict[str, ProdutoColetado | None] = {}  # produtos já consultados nesta coleta

    def _autenticar(self) -> None:
        """Token do app; vale 6 horas e é renovado quando a API responde 401."""
        r = self.http.post(
            "/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": _env("ML_CLIENT_ID"),
                "client_secret": _env("ML_CLIENT_SECRET"),
            },
        )
        r.raise_for_status()
        self.http.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    def _get(self, caminho: str, **params) -> httpx.Response:
        for tentativa in range(4):
            try:
                r = self.http.get(caminho, params=params)
                if r.status_code == 401:
                    self._autenticar()
                    continue
                if r.status_code != 429 and r.status_code < 500:
                    return r
            except httpx.TransportError:
                if tentativa == 3:
                    raise
            time.sleep(3 * (tentativa + 1))
        return r

    def _categorias_de(self, termo: str) -> list[dict]:
        """Categorias sugeridas para o termo. A primeira nem sempre é a certa ("cafe" → cafeteiras)."""
        if termo not in self._categorias:
            r = self._get("/sites/MLB/domain_discovery/search", q=termo, limit=CATEGORIAS)
            r.raise_for_status()
            self._categorias[termo] = list({c["category_id"]: c for c in r.json() or []}.values())
        return self._categorias[termo]

    def _consultar(self, ids: list[str], dados: dict[str, dict]) -> None:
        novos = list(dict.fromkeys(i for i in ids if i not in self._produtos))
        with ThreadPoolExecutor(PARALELO) as ex:
            for pid, p in zip(novos, ex.map(lambda i: self._produto(i, dados.get(i)), novos)):
                self._produtos[pid] = p

    def buscar(self, termo: str, pagina: int = 1) -> tuple[list[ProdutoColetado], int]:
        """Página 1: mais vendidos das categorias + 1ª página da busca; página 2: resto da busca."""
        categorias = self._categorias_de(termo)
        if not categorias:
            return [], 0
        ids: list[str] = []
        if pagina == 1:
            for cat in categorias:
                r = self._get(f"/highlights/MLB/category/{cat['category_id']}")
                if r.status_code == 200:
                    ids += [x["id"] for x in r.json().get("content", []) if x.get("type") == "PRODUCT"]
            self._consultar(ids, {})
        # a busca fica na categoria de mercado: a primeira cujos mais vendidos têm anúncio do Supermercado
        dominio = next((c["domain_id"] for c in categorias if c["domain_id"] in self._dominios_mercado), None)
        if dominio:
            r = self._get(
                "/products/search",
                status="active",
                site_id="MLB",
                q=termo,
                domain_id=dominio,
                limit=POR_PAGINA,
                offset=(pagina - 1) * POR_PAGINA,
            )
            r.raise_for_status()
            resultados = {p["id"]: p for p in r.json().get("results", [])}
            ids += list(resultados)
            self._consultar(ids, resultados)
        return [p for i in dict.fromkeys(ids) if (p := self._produtos.get(i))], PAGINAS if dominio else 1

    def _produto(self, pid: str, dados: dict | None) -> ProdutoColetado | None:
        r = self._get(f"/products/{pid}/items")
        if r.status_code != 200:
            return None  # produto sem anúncios ativos
        anuncios = [a for a in r.json().get("results", []) if SUPERMERCADO in a.get("tags", [])]
        if not anuncios:
            return None
        if dados is None:  # veio dos mais vendidos, que só trazem o id
            r = self._get(f"/products/{pid}")
            if r.status_code != 200:
                return None
            dados = r.json()
        self._dominios_mercado.add(dados.get("domain_id"))
        return converter(dados, min(anuncios, key=lambda a: a["price"]))


def converter(produto: dict, anuncio: dict) -> ProdutoColetado | None:
    nome = (produto.get("name") or "").strip()
    preco = anuncio.get("price")
    if not nome or not preco:
        return None
    original = anuncio.get("original_price")
    marca = next((a.get("value_name") for a in produto.get("attributes", []) if a.get("id") == "BRAND"), None)
    fotos = produto.get("pictures") or []
    return ProdutoColetado(
        sku=produto["id"],
        descricao=nome,
        preco=float(preco),
        marca=marca,
        preco_regular=float(original) if original and original > preco else None,
        url=f"https://www.mercadolivre.com.br/p/{produto['id']}",
        imagem=fotos[0].get("url") if fotos else None,
    )
