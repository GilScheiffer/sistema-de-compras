"""Busca na Amazon Brasil pela página de resultados.

A Amazon bloqueia robôs com frequência (resposta 503 ou captcha). Nesses casos a busca devolve
vazio em vez de quebrar a coleta, e os preços anteriores continuam valendo por alguns dias.
"""

from __future__ import annotations

import html
import re
import time

import httpx

from compras.coletores import ProdutoColetado

LOJA_ID = "amazon"
URL_BUSCA = "https://www.amazon.com.br/s"
PAGINAS = 1
PAUSA = 3.0

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


class Bloqueado(Exception):
    """A Amazon recusou a requisição (anti-robô)."""


class Cliente:
    def __init__(self):
        self.http = httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True)
        self._ultima = 0.0

    def buscar(self, termo: str, pagina: int = 1) -> tuple[list[ProdutoColetado], int]:
        espera = PAUSA - (time.monotonic() - self._ultima)
        if espera > 0:
            time.sleep(espera)
        params = {"k": termo, "i": "grocery"} | ({"page": str(pagina)} if pagina > 1 else {})
        for tentativa in range(3):
            r = self.http.get(URL_BUSCA, params=params)
            self._ultima = time.monotonic()
            if r.status_code == 200 and "captcha" not in r.text[:5000].lower():
                return extrair(r.text), PAGINAS
            time.sleep(10 * (tentativa + 1))
        raise Bloqueado(f"HTTP {r.status_code}")


_RE_BLOCO = re.compile(r'(?=<div[^>]+data-component-type="s-search-result")')


def extrair(pagina: str) -> list[ProdutoColetado]:
    produtos = {}
    for bloco in _RE_BLOCO.split(pagina)[1:]:
        p = converter(bloco)
        if p and p.sku not in produtos:
            produtos[p.sku] = p
    return list(produtos.values())


def _dinheiro(texto: str) -> float:
    return float(texto.replace("R$", "").replace("\xa0", "").replace(".", "").replace(",", ".").strip())


def converter(bloco: str) -> ProdutoColetado | None:
    asin = re.search(r'data-asin="([A-Z0-9]{10})"', bloco)
    titulo = re.search(r"<h2[^>]*>.*?<span[^>]*>(.*?)</span>", bloco, re.S)
    # O primeiro a-price que não é riscado nem preço por unidade é o preço de venda.
    preco = re.search(r'<span class="a-price"(?![^>]*a-text-price)[^>]*>\s*<span class="a-offscreen">([^<]+)</span>', bloco)
    if not (asin and titulo and preco):
        return None
    riscado = re.search(r'<span class="a-price a-text-price"[^>]*data-a-strike="true"[^>]*>\s*<span class="a-offscreen">([^<]+)</span>', bloco)
    imagem = re.search(r'<img[^>]+class="s-image"[^>]+src="([^"]+)"', bloco)
    valor = _dinheiro(preco.group(1))
    anterior = _dinheiro(riscado.group(1)) if riscado else None
    return ProdutoColetado(
        sku=asin.group(1),
        descricao=html.unescape(re.sub(r"<[^>]+>", "", titulo.group(1))).strip(),
        preco=valor,
        preco_regular=anterior if anterior and anterior > valor else None,
        url=f"https://www.amazon.com.br/dp/{asin.group(1)}",
        imagem=imagem.group(1) if imagem else None,
    )
