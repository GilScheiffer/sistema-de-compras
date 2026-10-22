"""Testa se cada loja responde à busca a partir desta máquina (útil rodando no GitHub Actions)."""

import subprocess

import httpx
from curl_cffi import requests as cr

from compras.coletores import amazon, mercado_livre

UA = amazon._HEADERS["User-Agent"]
TERMOS = ["arroz", "detergente"]


def relatar(nome, status, n):
    print(f"{nome:32} HTTP {status}  -> {n} produtos", flush=True)


for termo in TERMOS:
    url_ml = f"https://lista.mercadolivre.com.br/{termo}"
    r = httpx.get(url_ml, headers=mercado_livre._HEADERS, follow_redirects=True, timeout=30)
    relatar(f"ML httpx ({termo})", r.status_code, len(mercado_livre.extrair(r.text)))
    s = cr.Session(impersonate="chrome")
    r = s.get(url_ml, timeout=30)
    relatar(f"ML curl_cffi ({termo})", r.status_code, len(mercado_livre.extrair(r.text)))
    r = s.get(amazon.URL_BUSCA, params={"k": termo, "i": "grocery"}, timeout=30)
    relatar(f"Amazon curl_cffi ({termo})", r.status_code, len(amazon.extrair(r.text)))
    saida = subprocess.run(
        ["curl", "-s", "-L", "--compressed", f"https://www.amazon.com.br/s?k={termo}&i=grocery",
         "-H", f"User-Agent: {UA}", "-H", "Accept-Language: pt-BR,pt;q=0.9",
         "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
         "-w", "\n%{http_code}"], capture_output=True, text=True)
    corpo, _, status = saida.stdout.rpartition("\n")
    relatar(f"Amazon curl ({termo})", status, len(amazon.extrair(corpo)))
