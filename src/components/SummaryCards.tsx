import { fmtInt, fmtPct } from '../lib/helpers';
import type { SummaryRow } from '../lib/bundle';

interface Props {
  summary: SummaryRow | null;
  isLoading: boolean;
}

export default function SummaryCards({ summary, isLoading }: Props) {
  return (
    <div className="cards">
      {isLoading || !summary ? (
        <div className="card" style={{ gridColumn: '1/-1' }}>
          <div className="loading-wrap">
            <div className="spinner"></div><br />Carregando...
          </div>
        </div>
      ) : (
        <>
          <div className="card">
            <div className="card-label">Total de alunos</div>
            <div className="card-value">{fmtInt(summary.total_alunos)}</div>
            <div className="card-meta">Total esperado</div>
          </div>
          <div className="card">
            <div className="card-label">% Dia 1</div>
            <div className="card-value">{fmtPct(summary.perc_dia1)}</div>
            <div className="card-meta">Cartões lidos / total de estudantes</div>
          </div>
          <div className="card">
            <div className="card-label">% Dia 2</div>
            <div className="card-value">{fmtPct(summary.perc_dia2)}</div>
            <div className="card-meta">Cartões lidos / total de estudantes</div>
          </div>
        </>
      )}
    </div>
  );
}
