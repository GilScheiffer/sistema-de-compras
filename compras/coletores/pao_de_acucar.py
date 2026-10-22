"""Busca de produtos na loja online do Pão de Açúcar (mesma API que o site usa)."""

from __future__ import annotations

import time

import httpx

from compras.coletores import ProdutoColetado
from compras.texto import normalizar

LOJA_ID = "pao_de_acucar"
URL_BUSCA = "https://api.vendas.gpa.digital/pa/search/search"
URL_IMAGEM = "https://static.paodeacucar.com"
# Loja do Multicenter Itaipu (Niterói), escolhida pelo casal. Descoberta via
# api.vendas.gpa.digital/pa/delivery-v2/ecom/deliveryOptions?zipCode=24340000
STORE_ID = 2272
POR_PAGINA = 40
PAUSA = 0.7  # segundos entre requisições, para não sobrecarregar o site

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Origin": "https://www.paodeacucar.com",
    "Referer": "https://www.paodeacucar.com/",
}


class Cliente:
    def __init__(self, store_id: int = STORE_ID):
        self.store_id = store_id
        self.http = httpx.Client(headers=_HEADERS, timeout=30)
        self._ultima = 0.0

    def buscar(self, termo: str, pagina: int = 1) -> tuple[list[ProdutoColetado], int]:
        """Uma página de resultados e o total de páginas."""
        espera = PAUSA - (time.monotonic() - self._ultima)
        if espera > 0:
            time.sleep(espera)
        corpo = {
            "terms": normalizar(termo),  # a API recusa alguns termos acentuados
            "page": pagina,
            "sortBy": "relevance",
            "resultsPerPage": POR_PAGINA,
            "allowRedirect": True,
            "storeId": self.store_id,
            "department": "ecom",
            "customerPlus": True,
            "partner": "fallback",
        }
        for tentativa in range(3):
            try:
                r = self.http.post(URL_BUSCA, json=corpo)
                if r.status_code in (400, 404):
                    # termo que a busca não aceita (ou redireciona para landing page)
                    self._ultima = time.monotonic()
                    return [], 0
                r.raise_for_status()
                break
            except httpx.HTTPError:
                if tentativa == 2:
                    raise
                time.sleep(5 * (tentativa + 1))
        self._ultima = time.monotonic()
        dados = r.json()
        produtos = [converter(p) for p in dados.get("products", []) if _aproveitavel(p)]
        return produtos, int(dados.get("totalPages") or 1)


def _aproveitavel(p: dict) -> bool:
    # Produtos pesáveis (frutas, carnes no balcão) não têm tamanho fixo.
    return bool(p.get("stock")) and not p.get("variableWeight") and (p.get("price") or 0) > 0


def converter(p: dict) -> ProdutoColetado:
    promo = p.get("productPromotion")
    preco_regular = p.get("priceFrom") if p.get("priceFrom") and p["priceFrom"] > p["price"] else None
    detalhes = None
    if promo or preco_regular:
        promo = promo or {}
        detalhes = {
            k: v
            for k, v in {
                "inicio": promo.get("startDate"),
                "fim": promo.get("endDate"),
                "percentual": promo.get("promotionPercentOff"),
                "leve": promo.get("promotionQuantityBuy"),
                "pague": promo.get("promotionQuantityPayFor"),
                "preco_unitario": promo.get("unitPrice"),
                "so_app": promo.get("appExclusive") or None,
            }.items()
            if v is not None
        }
    imagens = p.get("productImages") or []
    return ProdutoColetado(
        sku=str(p["id"]),
        descricao=p["name"].strip(),
        preco=float(p["price"]),
        marca=(p.get("brand") or None),
        preco_regular=float(preco_regular) if preco_regular else None,
        promocao=detalhes or None,
        url=p.get("urlDetails"),
        imagem=URL_IMAGEM + imagens[0] if imagens else None,
    )
