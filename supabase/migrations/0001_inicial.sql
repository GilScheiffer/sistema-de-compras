-- Esquema inicial do sistema de compras.
-- Dados públicos (lojas, catálogo, produtos, preços) são lidos por qualquer usuário logado
-- e escritos apenas pelos robôs (service role). Dados da casa só são visíveis aos membros.

-- ---------------------------------------------------------------- lojas

create table public.lojas (
    id                 text primary key,
    nome               text not null,
    tipo               text not null check (tipo in ('fisica', 'online')),
    custo_visita       numeric(10, 2) not null default 0,
    frete              numeric(10, 2) not null default 0,
    frete_gratis_acima numeric(10, 2),
    frete_isento_se    text,  -- chave em casas.condicoes que zera o frete (ex.: amazon_prime)
    ativa              boolean not null default true
);

create table public.regras_loja (
    id         bigint generated always as identity primary key,
    loja_id    text not null references public.lojas on delete cascade,
    tipo       text not null check (tipo in ('desconto_marca')),
    marca      text,
    percentual numeric(5, 2) check (percentual > 0 and percentual < 100),
    condicao   text  -- chave em casas.condicoes exigida para a regra valer
);

-- ---------------------------------------------------------------- catálogo

-- Item genérico que a casa compra ("Arroz branco", "Detergente").
-- busca/incluir/excluir dizem aos robôs como reconhecer produtos das lojas.
create table public.catalogo (
    id        text primary key,
    nome      text not null,
    categoria text not null,
    unidade   text not null check (unidade in ('kg', 'L', 'un')),
    busca     text not null,
    incluir   text[] not null default '{}',
    excluir   text[] not null default '{}',
    ativo     boolean not null default true
);

-- ---------------------------------------------------------------- casa

create table public.casas (
    id             uuid primary key default gen_random_uuid(),
    nome           text not null,
    condicoes      jsonb not null default '{}',  -- ex.: {"cartao_pao_de_acucar": true}
    codigo_convite text not null unique default substr(md5(random()::text), 1, 8),
    criada_em      timestamptz not null default now()
);

create table public.casa_membros (
    casa_id uuid not null references public.casas on delete cascade,
    user_id uuid not null references auth.users on delete cascade,
    primary key (casa_id, user_id)
);

create table public.itens_casa (
    casa_id        uuid not null references public.casas on delete cascade,
    catalogo_id    text not null references public.catalogo on delete cascade,
    marcas         text[] not null default '{}',  -- vazio = qualquer marca
    consumo_mensal numeric check (consumo_mensal > 0),  -- na unidade do item; null = 1 embalagem
    na_lista       boolean not null default true,
    primary key (casa_id, catalogo_id)
);

-- ---------------------------------------------------------------- produtos e preços

create table public.produtos (
    id            bigint generated always as identity primary key,
    loja_id       text not null references public.lojas,
    sku           text not null,
    catalogo_id   text references public.catalogo on delete set null,
    descricao     text not null,
    marca         text,
    quantidade    numeric not null check (quantidade > 0),  -- na unidade base
    unidade       text not null check (unidade in ('kg', 'L', 'un')),
    url           text,
    imagem        text,
    preco         numeric(10, 2),  -- preço atual (cópia do último registro em precos)
    preco_regular numeric(10, 2),  -- preço "de" quando em promoção
    promocao      jsonb,           -- detalhes da promoção atual (validade, leve x pague y...)
    visto_em      timestamptz,     -- última vez que um robô encontrou o produto
    criado_em     timestamptz not null default now(),
    unique (loja_id, sku)
);
create index produtos_catalogo_idx on public.produtos (catalogo_id);

-- Histórico: um registro por mudança de preço (não por coleta).
create table public.precos (
    id            bigint generated always as identity primary key,
    produto_id    bigint not null references public.produtos on delete cascade,
    preco         numeric(10, 2) not null check (preco > 0),
    preco_regular numeric(10, 2),
    em_promocao   boolean not null default false,
    coletado_em   timestamptz not null default now(),
    fonte         text not null
);
create index precos_produto_idx on public.precos (produto_id, coletado_em desc);

create table public.coletas (
    id           bigint generated always as identity primary key,
    loja_id      text not null,
    iniciada_em  timestamptz not null default now(),
    terminada_em timestamptz,
    status       text not null default 'rodando' check (status in ('rodando', 'ok', 'erro')),
    produtos     integer,
    mudancas     integer,
    erro         text
);

-- ---------------------------------------------------------------- segurança

create function public.eh_membro(casa uuid) returns boolean
language sql stable security definer set search_path = ''
as $$
    select exists (
        select 1 from public.casa_membros
        where casa_id = casa and user_id = (select auth.uid())
    );
$$;

-- Cria uma casa e adiciona quem chamou como membro.
create function public.criar_casa(nome text) returns uuid
language plpgsql security definer set search_path = ''
as $$
declare
    nova uuid;
begin
    if auth.uid() is null then
        raise exception 'precisa estar logado';
    end if;
    insert into public.casas (nome) values (criar_casa.nome) returning id into nova;
    insert into public.casa_membros (casa_id, user_id) values (nova, auth.uid());
    return nova;
end;
$$;

-- Entra numa casa existente pelo código de convite.
create function public.entrar_na_casa(codigo text) returns uuid
language plpgsql security definer set search_path = ''
as $$
declare
    alvo uuid;
begin
    if auth.uid() is null then
        raise exception 'precisa estar logado';
    end if;
    select id into alvo from public.casas where codigo_convite = lower(trim(codigo));
    if alvo is null then
        raise exception 'código de convite inválido';
    end if;
    insert into public.casa_membros (casa_id, user_id) values (alvo, auth.uid()) on conflict do nothing;
    return alvo;
end;
$$;

revoke execute on function public.eh_membro, public.criar_casa, public.entrar_na_casa from public, anon;
grant execute on function public.eh_membro, public.criar_casa, public.entrar_na_casa to authenticated;

alter table public.lojas enable row level security;
alter table public.regras_loja enable row level security;
alter table public.catalogo enable row level security;
alter table public.casas enable row level security;
alter table public.casa_membros enable row level security;
alter table public.itens_casa enable row level security;
alter table public.produtos enable row level security;
alter table public.precos enable row level security;
alter table public.coletas enable row level security;

create policy "logados leem" on public.lojas for select to authenticated using (true);
create policy "logados leem" on public.regras_loja for select to authenticated using (true);
create policy "logados leem" on public.catalogo for select to authenticated using (true);
create policy "logados leem" on public.produtos for select to authenticated using (true);
create policy "logados leem" on public.precos for select to authenticated using (true);
create policy "logados leem" on public.coletas for select to authenticated using (true);

create policy "membros leem" on public.casas for select to authenticated using (public.eh_membro(id));
create policy "membros editam" on public.casas for update to authenticated
    using (public.eh_membro(id)) with check (public.eh_membro(id));

create policy "membros leem" on public.casa_membros for select to authenticated using (public.eh_membro(casa_id));
create policy "sair da casa" on public.casa_membros for delete to authenticated using (user_id = (select auth.uid()));

create policy "membros gerenciam" on public.itens_casa for all to authenticated
    using (public.eh_membro(casa_id)) with check (public.eh_membro(casa_id));

-- ---------------------------------------------------------------- dados iniciais

insert into public.lojas (id, nome, tipo, custo_visita, frete, frete_gratis_acima, frete_isento_se) values
    ('guanabara',     'Guanabara',     'fisica', 0, 0,     null,  null),
    ('pao_de_acucar', 'Pão de Açúcar', 'fisica', 0, 0,     null,  null),
    ('amazon',        'Amazon',        'online', 0, 20.00, 100.00, 'amazon_prime'),
    ('mercado_livre', 'Mercado Livre', 'online', 0, 20.00, 79.00,  null),
    ('shopee',        'Shopee',        'online', 0, 15.00, 50.00,  null);

insert into public.regras_loja (loja_id, tipo, marca, percentual, condicao) values
    ('pao_de_acucar', 'desconto_marca', 'Qualitá', 20, 'cartao_pao_de_acucar');
