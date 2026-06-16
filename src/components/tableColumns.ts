export type ActiveView = 'resumo' | 'seduc' | 'ure' | 'escola';

export interface ColumnDef {
  key: string;
  label: string;
  sortable: boolean;
  cls: string;
  kind: 'text' | 'int' | 'intAbbr' | 'pct';
}

export const COLUMNS: Record<ActiveView, ColumnDef[]> = {
  resumo: [
    { key: 'serie', label: 'Série', sortable: true, cls: 'td-serie', kind: 'text' },
    { key: 'total_alunos', label: 'Estudantes', sortable: true, cls: 'td-num', kind: 'intAbbr' },
    { key: 'lidos_dia1', label: 'Qtd Dia 1', sortable: true, cls: 'td-num', kind: 'intAbbr' },
    { key: 'perc_dia1', label: '% Dia 1', sortable: true, cls: 'td-num', kind: 'pct' },
    { key: 'lidos_dia2', label: 'Qtd Dia 2', sortable: true, cls: 'td-num', kind: 'intAbbr' },
    { key: 'perc_dia2', label: '% Dia 2', sortable: true, cls: 'td-num', kind: 'pct' },
  ],
  seduc: [
    { key: 'ure', label: 'URE', sortable: true, cls: 'td-name', kind: 'text' },
    { key: 'total_escolas', label: 'Escolas', sortable: true, cls: 'td-num', kind: 'int' },
    { key: 'total_turmas', label: 'Turmas', sortable: true, cls: 'td-num', kind: 'int' },
    { key: 'total_alunos', label: 'Estudantes', sortable: true, cls: 'td-num', kind: 'int' },
    { key: 'perc_dia1', label: '% Dia 1', sortable: true, cls: 'td-num', kind: 'pct' },
    { key: 'perc_dia2', label: '% Dia 2', sortable: true, cls: 'td-num', kind: 'pct' },
  ],
  ure: [
    { key: 'escola', label: 'Escola', sortable: true, cls: 'td-name', kind: 'text' },
    { key: 'total_turmas', label: 'Turmas', sortable: true, cls: 'td-num', kind: 'int' },
    { key: 'total_alunos', label: 'Estudantes', sortable: true, cls: 'td-num', kind: 'int' },
    { key: 'perc_dia1', label: '% Dia 1', sortable: true, cls: 'td-num', kind: 'pct' },
    { key: 'perc_dia2', label: '% Dia 2', sortable: true, cls: 'td-num', kind: 'pct' },
  ],
  escola: [
    { key: 'turma', label: 'Turma', sortable: true, cls: 'td-name', kind: 'text' },
    { key: 'serie', label: 'Série', sortable: true, cls: 'td-serie', kind: 'text' },
    { key: 'total_alunos', label: 'Estudantes', sortable: true, cls: 'td-num', kind: 'int' },
    { key: 'perc_dia1', label: '% Dia 1', sortable: true, cls: 'td-num', kind: 'pct' },
    { key: 'perc_dia2', label: '% Dia 2', sortable: true, cls: 'td-num', kind: 'pct' },
  ],
};
