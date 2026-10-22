"""Busca no Mercado Livre, só anúncios do Mercado Livre Supermercado.

A página de resultados traz os produtos num JSON embutido ("polycard"). Anúncios de vendedores
avulsos ficam de fora: costumam ser kits e preços inflados, que atrapalham a comparação.
"""

from __future__ import annotations

import json
import re
import time

import httpx

from compras.coletores import ProdutoColetado
from compras.texto import normalizar

LOJA_ID = "mercado_livre"
URL_BUSCA = "https://lista.mercadolivre.com.br/{termo}{pagina}"
POR_PAGINA = 48
PAGINAS = 2
PAUSA = 1.5

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
_JSON = json.JSONDecoder()


class Cliente:
    def __init__(self):
        self.http = httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True)
        self._ultima = 0.0

    def buscar(self, termo: str, pagina: int = 1) -> tuple[list[ProdutoColetado], int]:
        espera = PAUSA - (time.monotonic() - self._ultima)
        if espera > 0:
            time.sleep(espera)
        slug = normalizar(termo).replace(" ", "-")
        desde = f"_Desde_{(pagina - 1) * POR_PAGINA + 1}" if pagina > 1 else ""
        for tentativa in range(3):
            try:
                r = self.http.get(URL_BUSCA.format(termo=slug, pagina=desde))
                if r.status_code == 404:
                    self._ultima = time.monotonic()
                    return [], 0
                r.raise_for_status()
                break
            except httpx.HTTPError:
                if tentativa == 2:
                    raise
                time.sleep(5 * (tentativa + 1))
        self._ultima = time.monotonic()
        return extrair(r.text), PAGINAS


def extrair(pagina: str) -> list[ProdutoColetado]:
    vistos: dict[str, ProdutoColetado] = {}
    for m in re.finditer(r'"polycard":', pagina):
        try:
            card, _ = _JSON.raw_decode(pagina, m.end())
            p = converter(card)
        except (ValueError, KeyError, TypeError):
            continue
        if p and p.sku not in vistos:
            vistos[p.sku] = p
    return list(vistos.values())


def _supermercado(meta: dict) -> bool:
    evento = meta.get("tracks", {}).get("cart_tracks", {}).get("melidata_track", {}).get("event_data", {})
    return evento.get("flow_type") == "supermarket"


def converter(card: dict) -> ProdutoColetado | None:
    meta = card["metadata"]
    if not _supermercado(meta):
        return None
    comps = {c["type"]: c for c in card.get("components", [])}
    titulo = comps.get("title", {}).get("title", {}).get("text")
    preco_info = comps.get("price", {}).get("price", {})
    preco = (preco_info.get("current_price") or {}).get("value")
    if not titulo or not preco:
        return None
    anterior = None
    for rotulo in preco_info.get("price_labels", []):
        for v in rotulo.get("values", []):
            if v.get("key") == "previous_price":
                anterior = v.get("price", {}).get("value")
    fotos = card.get("pictures", {}).get("pictures", [])
    url = meta.get("url")
    return ProdutoColetado(
        sku=meta["id"],
        descricao=titulo.strip(),
        preco=float(preco),
        preco_regular=float(anterior) if anterior and anterior > preco else None,
        url=f"https://{url}" if url and not url.startswith("http") else url,
        imagem=f"https://http2.mlstatic.com/D_NQ_NP_{fotos[0]['id']}-O.webp" if fotos else None,
    )
