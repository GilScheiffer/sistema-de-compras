export type Unidade = "kg" | "L" | "un";

export interface Loja {
  id: string;
  nome: string;
  tipo: "fisica" | "online";
  custo_visita: number;
  frete: number;
  frete_gratis_acima: number | null;
  frete_isento_se: string | null;
}

export interface Regra {
  loja_id: string;
  tipo: "desconto_marca";
  marca: string | null;
  percentual: number | null;
  condicao: string | null;
}

export interface ItemCatalogo {
  id: string;
  nome: string;
  categoria: string;
  unidade: Unidade;
}

export interface Promocao {
  inicio?: string;
  fim?: string;
  percentual?: number;
  leve?: number;
  pague?: number;
  so_app?: boolean;
}

export interface Produto {
  id: number;
  loja_id: string;
  catalogo_id: string;
  descricao: string;
  marca: string | null;
  quantidade: number;
  unidade: Unidade;
  preco: number;
  preco_regular: number | null;
  promocao: Promocao | null;
  url: string | null;
  imagem: string | null;
  visto_em: string;
}

export interface Casa {
  id: string;
  nome: string;
  condicoes: Record<string, boolean>;
  codigo_convite: string;
}

export interface ItemCasa {
  casa_id: string;
  catalogo_id: string;
  marcas: string[];
  consumo_mensal: number | null;
  na_lista: boolean;
}
