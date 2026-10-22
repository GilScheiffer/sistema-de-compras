import { useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { normalizar } from "../calculo";
import { removerItem, salvarItem, type Dados } from "../dados";
import { nomeUnidade } from "../formato";
import type { ItemCasa, ItemCatalogo } from "../tipos";

interface Props {
  dados: Dados;
  setDados: Dispatch<SetStateAction<Dados | null>>;
}

export default function Itens({ dados, setDados }: Props) {
  const [busca, setBusca] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const casaId = dados.casa!.id;
  const escolhidos = useMemo(() => new Map(dados.itensCasa.map((i) => [i.catalogo_id, i])), [dados.itensCasa]);

  // Marcas que aparecem nas lojas para cada item, das mais comuns para as menos.
  const marcasPorItem = useMemo(() => {
    const contagem = new Map<string, Map<string, number>>();
    for (const p of dados.produtos) {
      if (!p.marca) continue;
      const m = contagem.get(p.catalogo_id) ?? new Map<string, number>();
      m.set(p.marca, (m.get(p.marca) ?? 0) + 1);
      contagem.set(p.catalogo_id, m);
    }
    return new Map([...contagem].map(([id, m]) => [id, [...m].sort((a, b) => b[1] - a[1]).map(([marca]) => marca)]));
  }, [dados.produtos]);

  const categorias = useMemo(() => {
    const termo = normalizar(busca);
    const grupos = new Map<string, ItemCatalogo[]>();
    for (const item of dados.catalogo) {
      if (termo && !normalizar(item.nome).includes(termo)) continue;
      grupos.set(item.categoria, [...(grupos.get(item.categoria) ?? []), item]);
    }
    return [...grupos].sort(([a], [b]) => a.localeCompare(b));
  }, [dados.catalogo, busca]);

  function atualizarLocal(fn: (itens: ItemCasa[]) => ItemCasa[]) {
    setDados((d) => (d ? { ...d, itensCasa: fn(d.itensCasa) } : d));
  }

  async function persistir(acao: () => Promise<void>, desfazer: () => void) {
    try {
      setErro(null);
      await acao();
    } catch (e) {
      desfazer();
      setErro(`Não salvou: ${e instanceof Error ? e.message : e}`);
    }
  }

  function alternar(item: ItemCatalogo) {
    const atual = escolhidos.get(item.id);
    if (atual) {
      atualizarLocal((l) => l.filter((i) => i.catalogo_id !== item.id));
      persistir(() => removerItem(casaId, item.id), () => atualizarLocal((l) => [...l, atual]));
    } else {
      const novo: ItemCasa = { casa_id: casaId, catalogo_id: item.id, marcas: [], consumo_mensal: null, na_lista: true };
      atualizarLocal((l) => [...l, novo]);
      persistir(() => salvarItem(novo), () => atualizarLocal((l) => l.filter((i) => i.catalogo_id !== item.id)));
    }
  }

  function editar(atual: ItemCasa, mudanca: Partial<ItemCasa>) {
    const novo = { ...atual, ...mudanca };
    atualizarLocal((l) => l.map((i) => (i.catalogo_id === atual.catalogo_id ? novo : i)));
    persistir(() => salvarItem(novo), () => atualizarLocal((l) => l.map((i) => (i.catalogo_id === atual.catalogo_id ? atual : i))));
  }

  return (
    <section>
      <div className="cabecalho-secao">
        <h2>O que vocês compram?</h2>
        <p className="sutil">
          Marque os itens da casa. Para cada um, dá para dizer quanto usam por mês e quais marcas aceitam. {escolhidos.size} escolhido(s).
        </p>
        <input type="search" placeholder="Buscar item…" value={busca} onChange={(e) => setBusca(e.target.value)} />
        {erro && <p className="erro">{erro}</p>}
      </div>

      {categorias.map(([categoria, itens]) => (
        <div key={categoria} className="grupo">
          <h3>{categoria}</h3>
          {itens.map((item) => {
            const escolhido = escolhidos.get(item.id);
            return (
              <div key={item.id} className={`item ${escolhido ? "escolhido" : ""}`}>
                <label className="item-linha">
                  <input type="checkbox" checked={!!escolhido} onChange={() => alternar(item)} />
                  <span>{item.nome}</span>
                </label>
                {escolhido && (
                  <Detalhes item={item} escolhido={escolhido} marcas={marcasPorItem.get(item.id) ?? []} editar={editar} />
                )}
              </div>
            );
          })}
        </div>
      ))}
    </section>
  );
}

function Detalhes({
  item,
  escolhido,
  marcas,
  editar,
}: {
  item: ItemCatalogo;
  escolhido: ItemCasa;
  marcas: string[];
  editar: (atual: ItemCasa, mudanca: Partial<ItemCasa>) => void;
}) {
  const [consumo, setConsumo] = useState(escolhido.consumo_mensal?.toString().replace(".", ",") ?? "");
  const [todasMarcas, setTodasMarcas] = useState(false);
  const selecionadas = new Set(escolhido.marcas);
  const visiveis = todasMarcas ? marcas : marcas.slice(0, 8);

  function salvarConsumo() {
    const valor = consumo.trim() ? Number(consumo.replace(",", ".")) : null;
    if (valor !== null && (!Number.isFinite(valor) || valor <= 0)) return setConsumo("");
    if (valor !== escolhido.consumo_mensal) editar(escolhido, { consumo_mensal: valor });
  }

  function alternarMarca(marca: string) {
    const novas = selecionadas.has(marca) ? escolhido.marcas.filter((m) => m !== marca) : [...escolhido.marcas, marca];
    editar(escolhido, { marcas: novas });
  }

  return (
    <div className="detalhes">
      <label className="consumo">
        Por mês:
        <input
          inputMode="decimal"
          placeholder="—"
          value={consumo}
          onChange={(e) => setConsumo(e.target.value)}
          onBlur={salvarConsumo}
          onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
        />
        <span className="sutil">{nomeUnidade[item.unidade]}(s)</span>
      </label>
      {marcas.length > 0 && (
        <div className="marcas">
          <span className="sutil">{selecionadas.size ? "Só estas marcas:" : "Qualquer marca (toque para restringir):"}</span>
          <div className="chips">
            {visiveis.map((m) => (
              <button key={m} className={`chip ${selecionadas.has(m) ? "ligado" : ""}`} onClick={() => alternarMarca(m)}>
                {m}
              </button>
            ))}
            {marcas.length > 8 && (
              <button className="chip mais" onClick={() => setTodasMarcas(!todasMarcas)}>
                {todasMarcas ? "menos" : `+${marcas.length - 8}`}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
