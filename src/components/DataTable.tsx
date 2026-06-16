import type { ColumnDef } from './tableColumns';
import { fmtInt, fmtIntAbbr, fmtPct } from '../lib/helpers';

export type Row = Record<string, string | number | null | undefined>;

function renderCell(row: Row, col: ColumnDef) {
  const raw = row[col.key];
  if (raw === null || raw === undefined || raw === '') return '—';
  if (col.kind === 'int') return fmtInt(Number(raw));
  if (col.kind === 'intAbbr') return fmtIntAbbr(Number(raw));
  if (col.kind === 'pct') {
    const n = Number(raw);
    const cls = n >= 80 ? 'pct-good' : n >= 50 ? 'pct-mid' : 'pct-low';
    return <span className={`pct-badge ${cls}`}>{fmtPct(n)}</span>;
  }
  return String(raw);
}

interface DataTableProps {
  columns: ColumnDef[];
  data: Row[];
  isLoading: boolean;
  sortConfig: { key: string; direction: 'asc' | 'desc' };
  onSort: (key: string) => void;
  onRowClick?: (row: Row) => void;
  variant?: 'default' | 'resumo';
}

export default function DataTable({ columns, data, isLoading, sortConfig, onSort, onRowClick, variant = 'default' }: DataTableProps) {
  return (
    <div className={`table-wrap ${variant === 'resumo' ? 'resumo' : ''}`}>
      <table>
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`${col.cls} ${sortConfig.key === col.key ? 'active-sort' : ''}`}
                data-sortable={col.sortable ? 'true' : 'false'}
                onClick={() => col.sortable && onSort(col.key)}
              >
                {col.label} {col.sortable && sortConfig.key === col.key && (sortConfig.direction === 'asc' ? '↑' : '↓')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr>
              <td colSpan={columns.length}>
                <div className="loading-wrap"><div className="spinner"></div><br />Conectando ao Supabase...</div>
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length}>
                <div className="notice">Nenhum dado encontrado.</div>
              </td>
            </tr>
          ) : (
            data.map((row, idx) => {
              const isTotal = row.serie === 'TOTAL';
              return (
              <tr
                key={idx}
                onClick={() => !isTotal && onRowClick?.(row)}
                className={isTotal ? 'row-total' : undefined}
                style={onRowClick && !isTotal ? { cursor: 'pointer' } : undefined}
              >
                {columns.map((col) => (
                  <td key={col.key} className={col.cls}>{renderCell(row, col)}</td>
                ))}
              </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
