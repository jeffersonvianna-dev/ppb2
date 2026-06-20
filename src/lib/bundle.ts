// Bundle estático pré-agregado, servido pela CDN do Vercel.
// Gerado por `scripts/build_bundle.py`. Sem fetch no Supabase em runtime.
//
// Split em dois arquivos para economizar bandwidth:
//   - /bundle.json (~100 KB brotli): core para RESUMO/SEDUC/URE.
//   - /turmas.json (~2.5 MB brotli): só baixa quando entra na aba ESCOLA.

export interface SummaryRow {
  total_alunos: number;
  total_lidos_dia1: number;
  total_lidos_dia2: number;
  total_lidos_dia3: number;
  total_alunos_dia3: number;
  perc_dia1: number;
  perc_dia2: number;
  perc_dia3: number | null;
}

export interface ResumoRow {
  serie: string;
  serie_order: number;
  total_alunos: number;
  lidos_dia1: number;
  lidos_dia2: number;
  lidos_dia3: number | null;
  perc_dia1: number;
  perc_dia2: number;
  perc_dia3: number | null;
}

export interface SeducRow {
  ure: string;
  total_escolas: number;
  total_turmas: number;
  total_alunos: number;
  perc_dia1: number;
  perc_dia2: number;
  perc_dia3: number | null;
}

export interface EscolaRow {
  ure: string;
  escola_id: string;
  escola: string;
  total_turmas: number;
  total_alunos: number;
  perc_dia1: number;
  perc_dia2: number;
  perc_dia3: number | null;
}

export interface TurmaRow {
  escola_id: string;
  turma_id: string;
  turma: string;
  serie: string | null;
  total_alunos: number;
  perc_dia1: number;
  perc_dia2: number;
  perc_dia3: number | null;
}

export interface Bundle {
  atualizacao: string | null;
  summary: SummaryRow;
  resumo: ResumoRow[];
  seduc: SeducRow[];
  escolas: EscolaRow[];
}

export interface TurmasBundle {
  atualizacao: string | null;
  turmas: TurmaRow[];
}

let bundleCache: Promise<Bundle> | null = null;
let turmasCache: Promise<TurmasBundle> | null = null;

export function loadBundle(): Promise<Bundle> {
  if (!bundleCache) {
    bundleCache = fetch('/bundle.json', { cache: 'default' }).then((r) => {
      if (!r.ok) throw new Error(`Falha ao carregar bundle: ${r.status}`);
      return r.json() as Promise<Bundle>;
    });
  }
  return bundleCache;
}

export function loadTurmas(): Promise<TurmasBundle> {
  if (!turmasCache) {
    turmasCache = fetch('/turmas.json', { cache: 'default' }).then((r) => {
      if (!r.ok) throw new Error(`Falha ao carregar turmas: ${r.status}`);
      return r.json() as Promise<TurmasBundle>;
    });
  }
  return turmasCache;
}
