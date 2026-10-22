import { describe, expect, it } from "vitest";
import { melhorPorLoja, ofertasDoItem, planejar, precoEfetivo } from "./calculo";
import type { ItemCasa, ItemCatalogo, Loja, Produto, Regra } from "./tipos";

const regras: Regra[] = [
  { loja_id: "pao_de_acucar", tipo: "desconto_marca", marca: "Qualitá", percentual: 20, condicao: "cartao_pao_de_acucar" },
];
const lojas: Loja[] = [
  { id: "guanabara", nome: "Guanabara", tipo: "fisica", custo_visita: 0, frete: 0, frete_gratis_acima: null, frete_isento_se: null },
  { id: "pao_de_acucar", nome: "Pão de Açúcar", tipo: "fisica", custo_visita: 0, frete: 0, frete_gratis_acima: null, frete_isento_se: null },
  { id: "mercado_livre", nome: "Mercado Livre", tipo: "online", custo_visita: 0, frete: 20, frete_gratis_acima: 79, frete_isento_se: null },
];

let seq = 0;
function produto(loja_id: string, catalogo_id: string, descricao: string, quantidade: number, preco: number, marca: string | null = null): Produto {
  return {
    id: ++seq, loja_id, catalogo_id, descricao, marca, quantidade, unidade: "kg", preco,
    preco_regular: null, promocao: null, url: null, imagem: null, visto_em: new Date().toISOString(),
  };
}
const item = (catalogo_id: string, consumo_mensal: number | null, marcas: string[] = []): ItemCasa => ({
  casa_id: "c", catalogo_id, marcas, consumo_mensal, na_lista: true,
});

describe("precoEfetivo", () => {
  it("aplica 20% na Qualitá só com o cartão", () => {
    const p = produto("pao_de_acucar", "arroz", "Arroz Branco Tipo 1 Qualitá Pacote 5kg", 5, 22.99, "QUALITÁ");
    expect(precoEfetivo(p, regras, { cartao_pao_de_acucar: true })).toEqual({ valor: 18.39, ajustes: ["-20% Qualitá"] });
    expect(precoEfetivo(p, regras, {}).valor).toBe(22.99);
  });
});

describe("ofertasDoItem", () => {
  const produtos = [
    produto("guanabara", "arroz", "Arroz 1kg", 1, 6, "TIO JOÃO"),
    produto("guanabara", "arroz", "Arroz 5kg", 5, 27, "TIO JOÃO"),
    produto("pao_de_acucar", "arroz", "Arroz Qualitá 5kg", 5, 30, "QUALITÁ"),
  ];
  it("escolhe pelo custo da necessidade", () => {
    const ofertas = ofertasDoItem(item("arroz", 5), produtos, regras, { cartao_pao_de_acucar: true });
    expect(ofertas[0].produto.descricao).toBe("Arroz Qualitá 5kg");
    expect(ofertas[0].custo).toBe(24);
    expect(melhorPorLoja(ofertas).get("guanabara")?.produto.descricao).toBe("Arroz 5kg");
  });
  it("respeita as marcas escolhidas", () => {
    const ofertas = ofertasDoItem(item("arroz", 5, ["Tio João"]), produtos, regras, { cartao_pao_de_acucar: true });
    expect(ofertas.every((o) => o.produto.marca === "TIO JOÃO")).toBe(true);
  });
});

describe("planejar", () => {
  it("divide entre lojas e considera o frete", () => {
    const produtos = [
      produto("guanabara", "arroz", "Arroz 5kg", 5, 28),
      produto("pao_de_acucar", "arroz", "Arroz Qualitá 5kg", 5, 30, "QUALITÁ"),
      produto("guanabara", "sabao", "Omo 1,6kg", 1.6, 35),
      produto("pao_de_acucar", "sabao", "Omo 1,6kg", 1.6, 38),
      produto("mercado_livre", "sabao", "Omo 1,6kg", 1.6, 25),
    ];
    const cond = { cartao_pao_de_acucar: true };
    const itensCasa = [item("arroz", 5), item("sabao", 1.6)];
    const porItem = new Map(itensCasa.map((i) => [i.catalogo_id, melhorPorLoja(ofertasDoItem(i, produtos, regras, cond))]));
    const cat: ItemCatalogo[] = [
      { id: "arroz", nome: "Arroz", categoria: "M", unidade: "kg" },
      { id: "sabao", nome: "Sabão", categoria: "L", unidade: "kg" },
    ];
    const planos = planejar(cat, porItem, lojas, cond);
    expect(planos[0].lojas.map((l) => l.id)).toEqual(["guanabara", "pao_de_acucar"]);
    expect(planos[0].total).toBe(59);
    const ml = planos.find((p) => p.lojas.some((l) => l.id === "mercado_livre"))!;
    expect(ml.custosFixos.get("mercado_livre")).toBe(20);
  });
});
