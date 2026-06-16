const MESES = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
];

function formatUpdated(iso: string | null): string {
  if (!iso) return 'Carregando...';
  const d = new Date(iso);
  const brt = new Date(d.getTime() - 3 * 60 * 60 * 1000);
  const dia = brt.getUTCDate();
  const mes = MESES[brt.getUTCMonth()];
  const hh = String(brt.getUTCHours()).padStart(2, '0');
  const mm = String(brt.getUTCMinutes()).padStart(2, '0');
  return `${dia} de ${mes}, ${hh}h${mm}`;
}

export default function Header({ atualizacao }: { atualizacao: string | null }) {
  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-left">
          <div className="header-title">
            <h1>PROVA PAULISTA 2º BIMESTRE</h1>
            <p>Inserção de cartões respostas</p>
          </div>
        </div>
        <div className="header-stamp">
          Atualizado em <strong>{formatUpdated(atualizacao)}</strong>
        </div>
      </div>
    </header>
  );
}
