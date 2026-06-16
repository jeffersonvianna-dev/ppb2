# PP B2 — Contexto para Claude

Dashboard de inserção de cartões-resposta da Prova Paulista (**Bimestre 2/2026**), com aba Resumo (por série) + drilldown SEDUC → URE → Escola → Turma. Em uso ativo durante os dias de prova — atualizado várias vezes por dia.

> Duplicado do projeto **ppb1** (Bimestre 1). Diferença principal: o ppb2 lê os dados **direto do CSV** (sem Supabase) — veja abaixo.

## Stack
- **Frontend:** React 19 + Vite 8 + TypeScript + TanStack React Query
- **Deploy:** Vercel auto-deploy do `main` → https://ppb2.vercel.app
- **Dados:** **bundle estático JSON na CDN do Vercel**, gerado **direto do CSV** dos Downloads
- **Supabase:** não usado (o ppb1 passava por Supabase; o ppb2 dispensa)

## Decisão arquitetural (importante)

**Front lê `/bundle.json` (core) + `/turmas.json` (lazy, só na aba ESCOLA) — NUNCA chama backend no runtime.**
Drilldown e filtros (busca, série) são `Array.filter()` em memória.

Trade-off aceito: bundle precisa ser regerado e committed quando os dados mudam — automatizado em `scripts/refresh.py`.

**Mudança vs ppb1:** o B2 recebe os dados como **CSV** (não xlsx) e o `build_bundle.py` agrega tudo em pandas, **sem Supabase**. Não precisa de senha de banco nem de migrations.

## Fluxo de atualização (várias vezes/dia)

```bash
# auto-detecta o CSV "Dia 1" (e "Dia 2", quando existir) mais recente nos Downloads
python scripts/refresh.py
```

`refresh.py` faz: build do bundle (~12s) → `git commit` + `git push` → Vercel deploy automático.
Sai cedo se o CSV não mudou (use `FORCE=1` para forçar).

**Sobrescrever o timestamp do header** (exibir hora diferente da do CSV):
```bash
STAMP_BRT="2026-06-16 15:00" python scripts/refresh.py
# ou só regerar o bundle, sem commit:
STAMP_BRT="2026-06-16 15:00" python scripts/build_bundle.py
```
O `STAMP_BRT` é horário de Brasília; o script converte para ISO com offset `-03:00`.
Sem `STAMP_BRT`, usa o máximo da coluna `Atualizacao` do CSV (tratada como BRT).

## Formato do CSV-fonte (`Dados Completos  Dia N-AAAA-MM-DD.csv`)

- **Encoding UTF-8** (apesar do console Windows exibir mojibake — `pd.read_csv(..., encoding="utf-8")` lê certo).
- Colunas usadas: `URE, Escola, Turma, Bimestre, DIA_PROVA, Total_Alunos_Turma, gabaritos_lidos_cmspp, Atualizacao, nome_prova_{Roxo,Laranja,Verde,Amarela}`.
- **Não tem `Tipo_Prova`** (o ppb1 filtrava por ele; aqui não existe e não é necessário).
- `serie` é derivada do primeiro `nome_prova_*` não-nulo (regex no dígito inicial; "ano"→EF, senão EM).
- Pode haver duplicatas em `(URE,Escola,Turma,DIA_PROVA)` → dedup mantendo a última.
- O arquivo "Dia 1" só traz `DIA_PROVA=1`; "Dia 2" (quando sair) traz `DIA_PROVA=2`. O build concatena os dois.

## Denominador / "total esperado" — DECISÃO CRÍTICA

⚠️ O export do B2 **só lista turmas que JÁ começaram a subir cartões** (toda linha
tem `gabaritos_lidos_cmspp > 0`; turmas pendentes não aparecem). Se somássemos só o
CSV, o "total esperado" ficaria ~794 mil e o "% Dia N" inflado (~73%).

Obs.: a base **tem** o esperado por turma (coluna `Total_Alunos_Turma`), mas só
das turmas presentes (somam 794k). Faltam ~57,5k turmas (~1,83 mi alunos).

**Denominador híbrido (esperado por turma):**
- turma **presente no B2** → usa o esperado do **próprio B2** (`Total_Alunos_Turma`);
- turma **só no universo** → usa o esperado do **B1** (`scripts/universe.json`,
  materializado do ppb1: **82.392 turmas / 2.628.034 alunos**).

`99,8%` das turmas do B2 casam por `turma_id = md5(ure|escola|turma)` com o universo,
e o esperado B2 vs B1 nas mesmas turmas difere só **~1%** → B1 é boa estimativa para as
pendentes. `universe.json` foi gerado de `ppb1/public/{bundle,turmas}.json`.

## Métricas

- `%DiaN = SUM(lidos_diaN do B2) / SUM(alunos esperados)` (esperado = híbrido acima)
- Turmas ainda sem leitura aparecem com **0%** (pendentes).
- `escola_id = md5(ure|escola)`, `turma_id = md5(ure|escola|turma)` (iguais ao ppb1)

## Snapshot — 16/jun 15h (dia 1 da prova B2)

82.443 turmas | 5.043 escolas | 91 UREs | **total esperado 2.620.861**
- D1: **22,16%** (580.721 lidos / 2,62 mi esperados) — 24.886 turmas já com leitura, 57.557 pendentes
- D2: 0% (dia 2 ainda não ocorreu)

## Estrutura

```
public/bundle.json + turmas.json  # gerados, COMMITTED
scripts/
  build_bundle.py                 # CSV (leituras) + universe.json (esperado) -> public/*.json
  universe.json                   # universo de turmas/alunos esperados (~82k turmas, do ppb1)
  refresh.py                      # build + commit + push
src/
  lib/bundle.ts                   # fetch único, cache: 'default' (revalida ETag)
  lib/helpers.ts                  # fmtInt, fmtPct
  components/
    Header.tsx                    # título "PROVA PAULISTA 2º BIMESTRE" + atualização BRT
    FilterSelect.tsx              # combobox c/ busca; prop `compact` (120px)
    SummaryCards.tsx              # 3 cards (total alunos / %D1 / %D2)
    DataTable.tsx                 # tabela genérica + variant resumo
    tableColumns.ts               # COLUMNS por aba
  App.tsx                         # estado, navegação por URL (pushState/popstate)
  main.tsx                        # QueryClient com staleTime: Infinity
vercel.json                       # Cache-Control para /bundle.json e /turmas.json
```

## UX/UI

- Tabs: **RESUMO / SEDUC / URE / ESCOLA** (caps, default = SEDUC)
- Resumo: tabela compacta centralizada com linha **TOTAL** azul pinned no fim
- Default sort alfabético em SEDUC/URE/Escola; por `serie_order` no Resumo
- Filtro **Série** aparece só em ESCOLA (compact, 120px, com "Todas")
- **Voltar do browser funcional**: estado serializado em URL (`?view=ure&ure=ADAMANTINA&escola_id=...`)
- Cores % badges: verde ≥80, âmbar ≥50, vermelho <50
- Cache: `staleTime: Infinity` no React Query + `cache: 'default'` no fetch (revalida via ETag a cada 5min)

## Pegadinhas conhecidas

- CSV-fonte é UTF-8; o console Windows mostra mojibake (`1Âª`, `sÃ©rie`) só na exibição — os dados estão corretos.
- Há um `turmas.csv` solto na raiz (dataset "Voar"/CIE, sem relação com este projeto) — está no `.gitignore`, não vai pro deploy.
