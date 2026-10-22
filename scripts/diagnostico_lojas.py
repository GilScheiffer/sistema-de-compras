"""Testa se cada loja responde à busca a partir desta máquina (útil rodando no GitHub Actions)."""

import re
import subprocess

from compras.coletores import mercado_livre

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def curl(url):
    saida = subprocess.run(
        ["curl", "-s", "-L", "--compressed", url, "-H", f"User-Agent: {UA}", "-H", "Accept-Language: pt-BR,pt;q=0.9",
         "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "-w", "\n%{http_code} %{url_effective}"],
        capture_output=True, text=True)
    corpo, _, fim = saida.stdout.rpartition("\n")
    return corpo, fim


for termo in ["arroz", "detergente", "cafe-pilao"]:
    corpo, fim = curl(f"https://lista.mercadolivre.com.br/{termo}")
    print(f"ML curl ({termo}): {fim[:90]} | {len(corpo)} bytes | polycards {corpo.count('\"polycard\":')} "
          f"| supermercado {corpo.count('\"flow_type\":\"supermarket\"')} | verificação {'account-verification' in fim + corpo[:3000]} "
          f"| extraídos {len(mercado_livre.extrair(corpo))}", flush=True)
    titulo = re.search(r"<title>(.*?)</title>", corpo)
    print("   título:", titulo.group(1)[:80] if titulo else None)
