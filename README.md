# Sistema de compras

Comparador de preços de mercado da casa: registra preços de várias lojas (Guanabara, Pão de Açúcar,
Amazon, Mercado Livre, Shopee...), aplica as regras de cada uma (ex.: -20% Qualitá com o cartão
Pão de Açúcar, frete grátis acima de X) e diz onde comprar cada item da lista para gastar menos.

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
```

## Uso

```powershell
# 1. cadastrar o que a casa compra (unidade: kg, L ou un)
compras item add Arroz -u kg -c mercearia
compras item add "Papel higiênico" -u un -c limpeza

# 2. registrar preços vistos (o tamanho é lido da descrição; senão use --qtd)
compras preco add guanabara arroz "Arroz Tio João Tipo 1 5kg" 27,90
compras preco add pao_de_acucar arroz "Arroz Qualitá Tipo 1 5kg" 29,90
compras preco add guanabara cafe "Café Pilão 500g" 17,99 --promo

# 3. montar a lista do mês
compras lista add arroz 5kg
compras lista add "papel higiênico" 24

# 4. comparar
compras comparar            # até 2 lojas por plano
compras comparar -n 3       # aceita dividir em até 3 lojas

compras preco historico cafe
compras lojas
```

Lojas, fretes e regras de desconto ficam em [config.toml](config.toml).

## Arquitetura

```
compras/
  config.py      lojas, regras e perfil (config.toml)
  db.py          SQLite: itens, produtos, histórico de preços, lista
  unidades.py    "5kg", "900ml", "6x350ml", "12 rolos" -> kg / L / un
  regras.py      descontos por loja (ex.: desconto_marca)
  comparador.py  melhor oferta por loja + plano com combinação de lojas e frete
  cli.py         comandos
```

- **Item** é o que a casa precisa ("Arroz", em kg). **Produto** é o SKU concreto numa loja
  ("Arroz Qualitá 5kg" no Pão de Açúcar). Assim dá pra comparar marcas e embalagens diferentes pelo R$/kg.
- Os preços nunca são sobrescritos, viram histórico. É ele que diz se uma "promoção" é de verdade.
- O plano testa todas as combinações de até N lojas e soma frete (online) ou custo de ida (física).

## Roadmap

1. ~~Núcleo + CLI + registro manual~~
2. **Coleta automática**
   - NFC-e: ler o QR code da nota fiscal e importar todos os itens com o preço real pago (Guanabara, Pão de Açúcar)
   - Pão de Açúcar online, Mercado Livre, Amazon (busca por produto)
   - Shopee por último (bloqueio anti-robô pesado)
3. Encartes/ofertas da semana + alerta de "promoção real" (abaixo da média histórica)
4. Interface web pelo celular, com a lista compartilhada entre os dois
5. Lista recorrente: consumo médio por mês e sugestão de quando estocar
