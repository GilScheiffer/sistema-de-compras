import { useCallback, useEffect, useState } from "react";
import { supabase } from "./supabase";
import type { Casa, ItemCasa, ItemCatalogo, Loja, Produto, Regra } from "./tipos";

// Produto que nenhum robô viu nos últimos dias provavelmente saiu de linha ou acabou.
const VALIDADE_DIAS = 3;
const PAGINA = 1000;

function checar<T>({ data, error }: { data: T | null; error: { message: string } | null }): T {
  if (error) throw new Error(error.message);
  return data as T;
}

async function produtosRecentes(): Promise<Produto[]> {
  const desde = new Date(Date.now() - VALIDADE_DIAS * 86400_000).toISOString();
  const todos: Produto[] = [];
  for (let inicio = 0; ; inicio += PAGINA) {
    const pagina = checar(
      await supabase
        .from("produtos")
        .select("id,loja_id,catalogo_id,descricao,marca,quantidade,unidade,preco,preco_regular,promocao,url,imagem,visto_em")
        .gte("visto_em", desde)
        .not("catalogo_id", "is", null)
        .order("id")
        .range(inicio, inicio + PAGINA - 1),
    ) as Produto[];
    todos.push(...pagina);
    if (pagina.length < PAGINA) return todos;
  }
}

export interface Dados {
  casa: Casa | null;
  itensCasa: ItemCasa[];
  catalogo: ItemCatalogo[];
  lojas: Loja[];
  regras: Regra[];
  produtos: Produto[];
  ultimaColeta: string | null;
}

export function useDados() {
  const [dados, setDados] = useState<Dados | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      const [casas, catalogo, lojas, regras, produtos, coletas] = await Promise.all([
        supabase.from("casas").select("*").limit(1).then(checar),
        supabase.from("catalogo").select("id,nome,categoria,unidade").eq("ativo", true).order("nome").then(checar),
        supabase.from("lojas").select("*").eq("ativa", true).then(checar),
        supabase.from("regras_loja").select("*").then(checar),
        produtosRecentes(),
        supabase.from("coletas").select("terminada_em").eq("status", "ok").order("terminada_em", { ascending: false }).limit(1).then(checar),
      ]);
      const casa = ((casas as Casa[])[0] ?? null) as Casa | null;
      const itensCasa = casa
        ? (checar(await supabase.from("itens_casa").select("*").eq("casa_id", casa.id)) as ItemCasa[])
        : [];
      setDados({
        casa,
        itensCasa,
        catalogo: catalogo as ItemCatalogo[],
        lojas: lojas as Loja[],
        regras: regras as Regra[],
        produtos,
        ultimaColeta: (coletas as { terminada_em: string }[])[0]?.terminada_em ?? null,
      });
      setErro(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  return { dados, setDados, erro, recarregar: carregar };
}

// --- escritas --------------------------------------------------------------

export async function criarCasa(nome: string) {
  checar(await supabase.rpc("criar_casa", { nome }));
}

export async function entrarNaCasa(codigo: string) {
  checar(await supabase.rpc("entrar_na_casa", { codigo }));
}

export async function salvarCondicoes(casa: Casa, condicoes: Record<string, boolean>) {
  checar(await supabase.from("casas").update({ condicoes }).eq("id", casa.id));
}

export async function salvarItem(item: ItemCasa) {
  checar(await supabase.from("itens_casa").upsert(item, { onConflict: "casa_id,catalogo_id", defaultToNull: false }));
}

export async function removerItem(casaId: string, catalogoId: string) {
  checar(await supabase.from("itens_casa").delete().eq("casa_id", casaId).eq("catalogo_id", catalogoId));
}
