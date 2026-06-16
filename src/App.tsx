import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Header from './components/Header';
import FilterSelect from './components/FilterSelect';
import SummaryCards from './components/SummaryCards';
import DataTable from './components/DataTable';
import { COLUMNS, type ActiveView } from './components/tableColumns';
import { loadBundle, loadTurmas, type Bundle, type TurmasBundle } from './lib/bundle';

type SortConfig = { key: string; direction: 'asc' | 'desc' };

type Row = Record<string, string | number | null | undefined>;

interface NavState {
  view: ActiveView;
  ure: string;
  escola_id: string;
}

const VALID_VIEWS: ActiveView[] = ['resumo', 'seduc', 'ure', 'escola'];

function readUrl(): NavState {
  const params = new URLSearchParams(window.location.search);
  const v = params.get('view') as ActiveView | null;
  return {
    view: v && VALID_VIEWS.includes(v) ? v : 'seduc',
    ure: params.get('ure') ?? '',
    escola_id: params.get('escola_id') ?? '',
  };
}

function writeUrl(s: NavState, replace: boolean) {
  const params = new URLSearchParams();
  params.set('view', s.view);
  if (s.ure) params.set('ure', s.ure);
  if (s.escola_id) params.set('escola_id', s.escola_id);
  const url = `${window.location.pathname}?${params.toString()}`;
  if (replace) window.history.replaceState(s, '', url);
  else window.history.pushState(s, '', url);
}

export default function App() {
  const initial = typeof window !== 'undefined' ? readUrl() : { view: 'seduc' as ActiveView, ure: '', escola_id: '' };
  const [activeView, setActiveViewRaw] = useState<ActiveView>(initial.view);
  const [selectedUre, setSelectedUre] = useState(initial.ure);
  const [selectedEscolaId, setSelectedEscolaId] = useState(initial.escola_id);
  const [selectedEscolaLabel, setSelectedEscolaLabel] = useState('');
  const [search, setSearch] = useState('');
  const [serieFilter, setSerieFilter] = useState('');
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'ure', direction: 'asc' });

  const NAME_KEY: Record<ActiveView, string> = {
    resumo: 'serie_order',
    seduc: 'ure',
    ure: 'escola',
    escola: 'turma',
  };

  useEffect(() => {
    setSearch('');
    setSerieFilter('');
    if (activeView === 'resumo') {
      setSortConfig({ key: 'perc_dia2', direction: 'asc' });
    } else {
      setSortConfig({ key: NAME_KEY[activeView], direction: 'asc' });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView]);

  // Navigation: update URL, support browser back
  const navigate = (next: Partial<NavState>) => {
    const view = next.view ?? activeView;
    const ure = next.ure ?? selectedUre;
    const escola_id = next.escola_id ?? selectedEscolaId;
    writeUrl({ view, ure, escola_id }, false);
    setActiveViewRaw(view);
    setSelectedUre(ure);
    setSelectedEscolaId(escola_id);
  };
  const setActiveView = (v: ActiveView) => navigate({ view: v });

  useEffect(() => {
    // Replace initial entry so first back goes elsewhere, not stays here
    writeUrl({ view: activeView, ure: selectedUre, escola_id: selectedEscolaId }, true);
    const onPop = () => {
      const s = readUrl();
      setActiveViewRaw(s.view);
      setSelectedUre(s.ure);
      setSelectedEscolaId(s.escola_id);
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data: bundle, isLoading } = useQuery<Bundle>({
    queryKey: ['bundle'],
    queryFn: loadBundle,
  });
  const { data: turmasBundle, isLoading: isLoadingTurmas } = useQuery<TurmasBundle>({
    queryKey: ['turmas'],
    queryFn: loadTurmas,
    enabled: activeView === 'escola',
  });

  const ureList = useMemo(() => (bundle ? bundle.seduc.map((r) => r.ure) : []), [bundle]);

  const resolvedUre = useMemo(() => {
    if (ureList.length === 0) return '';
    return ureList.includes(selectedUre) ? selectedUre : ureList[0];
  }, [ureList, selectedUre]);

  const escolasByUre = useMemo(() => {
    if (!bundle) return [] as typeof bundle extends Bundle ? Bundle['escolas'] : never[];
    return bundle.escolas.filter((e) => e.ure === resolvedUre);
  }, [bundle, resolvedUre]);

  const resolvedEscolaId = useMemo(() => {
    if (escolasByUre.length === 0) return '';
    return escolasByUre.find((e) => e.escola_id === selectedEscolaId)?.escola_id ?? escolasByUre[0].escola_id;
  }, [escolasByUre, selectedEscolaId]);

  useEffect(() => {
    if (!selectedEscolaLabel && resolvedEscolaId && bundle) {
      const e = bundle.escolas.find((x) => x.escola_id === resolvedEscolaId);
      if (e) setSelectedEscolaLabel(e.escola);
    }
  }, [resolvedEscolaId, selectedEscolaLabel, bundle]);

  const turmasByEscola = useMemo(() => {
    if (!turmasBundle) return [];
    return turmasBundle.turmas.filter((t) => t.escola_id === resolvedEscolaId);
  }, [turmasBundle, resolvedEscolaId]);

  const rawData: Row[] = useMemo(() => {
    if (!bundle) return [];
    if (activeView === 'resumo') return bundle.resumo as unknown as Row[];
    if (activeView === 'seduc') return bundle.seduc as unknown as Row[];
    if (activeView === 'ure') {
      return bundle.escolas.filter((e) => e.ure === resolvedUre) as unknown as Row[];
    }
    return turmasByEscola as unknown as Row[];
  }, [bundle, activeView, resolvedUre, turmasByEscola]);

  const availableSeries = useMemo(() => {
    if (activeView !== 'escola') return [] as string[];
    const order = ['4EF', '5EF', '6EF', '7EF', '8EF', '9EF', '1EM', '2EM', '3EM'];
    const found = new Set(turmasByEscola.map((r) => r.serie ?? '').filter(Boolean));
    return order.filter((s) => found.has(s));
  }, [turmasByEscola, activeView]);

  const visibleData = useMemo(() => {
    let rows: Row[] = [...rawData];
    if (activeView === 'escola' && serieFilter) {
      rows = rows.filter((r) => String(r.serie) === serieFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      const key =
        activeView === 'resumo' ? 'serie' :
        activeView === 'seduc' ? 'ure' :
        activeView === 'ure' ? 'escola' : 'turma';
      rows = rows.filter((r) => String(r[key] ?? '').toLowerCase().includes(q));
    }
    const preserveOrder = activeView === 'resumo' && sortConfig.key === 'perc_dia2' && sortConfig.direction === 'asc';
    if (!preserveOrder) {
      rows.sort((a, b) => {
        const va = a[sortConfig.key];
        const vb = b[sortConfig.key];
        if (typeof va === 'string' || typeof vb === 'string') {
          const ta = String(va ?? '');
          const tb = String(vb ?? '');
          return sortConfig.direction === 'asc' ? ta.localeCompare(tb, 'pt-BR') : tb.localeCompare(ta, 'pt-BR');
        }
        const na = Number(va ?? 0);
        const nb = Number(vb ?? 0);
        return sortConfig.direction === 'asc' ? na - nb : nb - na;
      });
    }
    if (activeView === 'resumo' && bundle && rawData.length > 0) {
      rows.push({
        serie: 'TOTAL',
        total_alunos: bundle.summary.total_alunos,
        lidos_dia1: bundle.summary.total_lidos_dia1,
        lidos_dia2: bundle.summary.total_lidos_dia2,
        perc_dia1: Number(bundle.summary.perc_dia1),
        perc_dia2: Number(bundle.summary.perc_dia2),
      });
    }
    return rows;
  }, [rawData, search, serieFilter, sortConfig, activeView, bundle]);

  const handleSort = (key: string) => {
    if (sortConfig.key === key) {
      setSortConfig({ key, direction: sortConfig.direction === 'asc' ? 'desc' : 'asc' });
    } else {
      setSortConfig({ key, direction: 'asc' });
    }
  };

  const handleRowClick = (row: Row) => {
    if (activeView === 'seduc' && row.ure) {
      navigate({ view: 'ure', ure: String(row.ure), escola_id: '' });
    } else if (activeView === 'ure' && row.escola_id) {
      setSelectedEscolaLabel(String(row.escola ?? ''));
      navigate({ view: 'escola', escola_id: String(row.escola_id) });
    }
  };

  const ureOptions = ureList.map((u) => ({ value: u, label: u }));
  const escolaOptions = escolasByUre.map((e) => ({ value: e.escola_id, label: e.escola }));

  return (
    <div>
      <Header atualizacao={bundle?.atualizacao ?? null} />
      <main className="page">
        <SummaryCards summary={bundle?.summary ?? null} isLoading={isLoading} />

        <div className="table-section">
          <div className="table-top">
            <div className="tabs">
              <button className={`tab-button ${activeView === 'resumo' ? 'active' : ''}`} onClick={() => setActiveView('resumo')}>RESUMO</button>
              <button className={`tab-button ${activeView === 'seduc' ? 'active' : ''}`} onClick={() => setActiveView('seduc')}>SEDUC</button>
              <button className={`tab-button ${activeView === 'ure' ? 'active' : ''}`} onClick={() => setActiveView('ure')}>URE</button>
              <button className={`tab-button ${activeView === 'escola' ? 'active' : ''}`} onClick={() => setActiveView('escola')}>ESCOLA</button>
            </div>

            <div className="table-filters">
              {(activeView === 'ure' || activeView === 'escola') && (
                <FilterSelect
                  label="URE"
                  options={ureOptions}
                  value={resolvedUre}
                  onChange={(v) => navigate({ ure: v, escola_id: '' })}
                  placeholder="Selecione"
                  searchPlaceholder="Buscar URE..."
                />
              )}
              {activeView === 'escola' && (
                <FilterSelect
                  label="Escola"
                  options={escolaOptions}
                  value={resolvedEscolaId}
                  onChange={(v) => {
                    const opt = escolaOptions.find((o) => o.value === v);
                    if (opt) setSelectedEscolaLabel(opt.label);
                    navigate({ escola_id: v });
                  }}
                  placeholder="Selecione"
                  searchPlaceholder="Buscar escola..."
                />
              )}
              {activeView === 'escola' && availableSeries.length > 0 && (
                <FilterSelect
                  label="Série"
                  options={[{ value: '', label: 'Todas' }, ...availableSeries.map((s) => ({ value: s, label: s }))]}
                  value={serieFilter}
                  onChange={setSerieFilter}
                  placeholder="Todas"
                  searchPlaceholder="Buscar..."
                  compact
                />
              )}
              <div className="field field-inline search-field">
                <label htmlFor="search">Busca</label>
                <input
                  id="search"
                  type="search"
                  placeholder="Filtrar..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>
          </div>

          {activeView === 'escola' && selectedEscolaLabel && (
            <div className="table-subheader">
              Turmas de <strong>{selectedEscolaLabel}</strong>
            </div>
          )}

          <DataTable
            columns={COLUMNS[activeView]}
            data={visibleData}
            isLoading={isLoading || (activeView === 'escola' && isLoadingTurmas)}
            sortConfig={sortConfig}
            onSort={handleSort}
            onRowClick={activeView === 'seduc' || activeView === 'ure' ? handleRowClick : undefined}
            variant={activeView === 'resumo' ? 'resumo' : 'default'}
          />
        </div>
      </main>
    </div>
  );
}
