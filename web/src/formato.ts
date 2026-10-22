import type { Unidade } from "./tipos";

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export const brl = (v: number) => moeda.format(v);

export function qtd(valor: number, unidade: Unidade): string {
  let v = valor;
  let u: string = unidade;
  if (unidade === "kg" && v < 1) [v, u] = [v * 1000, "g"];
  if (unidade === "L" && v < 1) [v, u] = [v * 1000, "ml"];
  return `${v.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ${u}`;
}

export const nomeUnidade: Record<Unidade, string> = { kg: "kg", L: "litro", un: "unidade" };

export function data(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export function quandoFoi(iso: string): string {
  const horas = (Date.now() - new Date(iso).getTime()) / 3600_000;
  if (horas < 1) return "agora há pouco";
  if (horas < 24) return `há ${Math.floor(horas)}h`;
  return `há ${Math.floor(horas / 24)} dia(s)`;
}
