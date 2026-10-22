// Comparação de preços e plano de compra (mesma lógica de compras/comparador.py).
import type { ItemCasa, ItemCatalogo, Loja, Produto, Regra } from "./tipos";

export function normalizar(texto: string): string {
  return texto
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/-/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
}

export interface Oferta {
  produto: Produto;
  efetivo: number; // preço da embalagem após descontos da loja
  ajustes: string[]; // ex.: "-20% Qualitá"
  pacotes: number;
  custo: number; // pacotes * efetivo
  porUnidade: number; // efetivo por kg / L / un
}

export function precoEfetivo(produto: Produto, regras: Regra[], condicoes: Record<string, boolean>) {
  let valor = produto.preco;
  const ajustes: string[] = [];
  for (const r of regras) {
    if (r.loja_id !== produto.loja_id) continue;
    if (r.condicao && !condicoes[r.condicao]) continue;
    if (r.tipo === "desconto_marca" && r.marca && r.percentual) {
      const alvo = ` ${normalizar(r.marca)} `;
      if (` ${normalizar(`${produto.marca ?? ""} ${produto.descricao}`)} `.includes(alvo)) {
        valor *= 1 - r.percentual / 100;
        ajustes.push(`-${r.percentual}% ${r.marca}`);
      }
    }
  }
  return { valor: Math.round(valor * 100) / 100, ajustes };
}

export function oferta(
  produto: Produto,
  necessidade: number | null,
  regras: Regra[],
  condicoes: Record<string, boolean>,
): Oferta {
  const { valor, ajustes } = precoEfetivo(produto, regras, condicoes);
  const pacotes = necessidade ? Math.max(1, Math.ceil(Number((necessidade / produto.quantidade).toFixed(6)))) : 1;
  return {
    produto,
    efetivo: valor,
    ajustes,
    pacotes,
    custo: Math.round(pacotes * valor * 100) / 100,
    porUnidade: valor / produto.quantidade,
  };
}

/** Ofertas de um item, da melhor para a pior, respeitando as marcas escolhidas. */
export function ofertasDoItem(
  item: ItemCasa,
  produtos: Produto[],
  regras: Regra[],
  condicoes: Record<string, boolean>,
): Oferta[] {
  const marcas = new Set(item.marcas.map(normalizar));
  return produtos
    .filter((p) => p.catalogo_id === item.catalogo_id)
    .filter((p) => marcas.size === 0 || (p.marca !== null && marcas.has(normalizar(p.marca))))
    .map((p) => oferta(p, item.consumo_mensal, regras, condicoes))
    .sort((a, b) =>
      item.consumo_mensal ? a.custo - b.custo || a.porUnidade - b.porUnidade : a.porUnidade - b.porUnidade || a.custo - b.custo,
    );
}

/** A melhor oferta de cada loja (a lista já vem ordenada da melhor para a pior). */
export function melhorPorLoja(ofertas: Oferta[]): Map<string, Oferta> {
  const m = new Map<string, Oferta>();
  for (const o of ofertas) if (!m.has(o.produto.loja_id)) m.set(o.produto.loja_id, o);
  return m;
}

export function custoFixo(loja: Loja, subtotal: number, condicoes: Record<string, boolean>): number {
  if (loja.tipo === "fisica") return loja.custo_visita;
  if (loja.frete_isento_se && condicoes[loja.frete_isento_se]) return 0;
  if (loja.frete_gratis_acima !== null && subtotal >= loja.frete_gratis_acima) return 0;
  return loja.frete;
}

export interface Plano {
  lojas: Loja[];
  alocacao: Map<string, Oferta>; // catalogo_id -> oferta escolhida
  faltando: ItemCatalogo[];
  subtotais: Map<string, number>;
  custosFixos: Map<string, number>;
  total: number;
}

function combinacoes<T>(lista: T[], k: number): T[][] {
  if (k === 0) return [[]];
  return lista.flatMap((x, i) => combinacoes(lista.slice(i + 1), k - 1).map((resto) => [x, ...resto]));
}

/** Todas as combinações úteis de até `maxLojas` lojas: menos itens faltando primeiro, depois menor total. */
export function planejar(
  itens: ItemCatalogo[],
  porItem: Map<string, Map<string, Oferta>>,
  lojas: Loja[],
  condicoes: Record<string, boolean>,
  maxLojas = 2,
): Plano[] {
  const candidatas = lojas.filter((l) => [...porItem.values()].some((m) => m.has(l.id)));
  const planos: Plano[] = [];
  for (let k = 1; k <= Math.min(maxLojas, candidatas.length); k++) {
    for (const combo of combinacoes(candidatas, k)) {
      const alocacao = new Map<string, Oferta>();
      const subtotais = new Map<string, number>();
      const faltando: ItemCatalogo[] = [];
      for (const item of itens) {
        const disponiveis = combo.map((l) => porItem.get(item.id)?.get(l.id)).filter((o): o is Oferta => !!o);
        if (disponiveis.length === 0) {
          faltando.push(item);
          continue;
        }
        const escolhida = disponiveis.reduce((a, b) => (b.custo < a.custo ? b : a));
        alocacao.set(item.id, escolhida);
        subtotais.set(escolhida.produto.loja_id, (subtotais.get(escolhida.produto.loja_id) ?? 0) + escolhida.custo);
      }
      if (subtotais.size < combo.length) continue; // uma combinação menor já cobre
      const custosFixos = new Map(combo.map((l) => [l.id, custoFixo(l, subtotais.get(l.id)!, condicoes)]));
      const total = [...subtotais.values(), ...custosFixos.values()].reduce((a, b) => a + b, 0);
      planos.push({ lojas: combo, alocacao, faltando, subtotais, custosFixos, total: Math.round(total * 100) / 100 });
    }
  }
  return planos.sort((a, b) => a.faltando.length - b.faltando.length || a.total - b.total || a.lojas.length - b.lojas.length);
}
