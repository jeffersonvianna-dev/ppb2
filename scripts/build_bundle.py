"""
Gera public/bundle.json (core) e public/turmas.json (lazy) da Prova Paulista B2.

IMPORTANTE — denominador / "total esperado":
    O export do B2 (CSV) só lista turmas que JÁ começaram a subir cartões
    (toda linha tem gabaritos_lidos_cmspp > 0). As turmas que ainda não
    iniciaram NÃO estão no arquivo. Se somássemos só o que está no CSV, o
    "total de alunos esperado" ficaria subdimensionado (~794 mil) e o "% Dia N"
    ficaria inflado.

    Denominador (esperado por turma), híbrido:
      - turma presente no B2 -> usa o esperado do PRÓPRIO B2 (Total_Alunos_Turma);
      - turma só no universo  -> usa o esperado do B1 (`scripts/universe.json`,
        materializado do ppb1: ~82.392 turmas / ~2,63 mi alunos).
    99,8% das turmas do B2 casam por turma_id = md5(ure|escola|turma) com o
    universo, e o esperado B2 vs B1 nas mesmas turmas difere só ~1% — então o
    B1 é uma boa estimativa para as ~57,5k turmas que ainda não viraram linha.

    Resultado: %DiaN = lidos (do B2) / alunos esperados. Turmas ainda sem
    leitura aparecem com 0% (pendentes).

bundle.json é baixado em todo carregamento (RESUMO/SEDUC/URE).
turmas.json só é baixado quando o usuário entra na aba ESCOLA.

Uso:
    python scripts/build_bundle.py
    CSV_DIA1=".../Dia 1-....csv" STAMP_BRT="2026-06-16 15:00" python scripts/build_bundle.py
"""
import glob
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "public"
OUT = OUT_DIR / "bundle.json"
OUT_TURMAS = OUT_DIR / "turmas.json"
UNIVERSE = ROOT / "scripts" / "universe.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOADS = Path(os.path.expanduser("~")) / "Downloads"


def latest(pattern):
    hits = sorted(glob.glob(str(DOWNLOADS / pattern)), key=os.path.getmtime)
    return hits[-1] if hits else None


CSV_DIA1 = os.environ.get("CSV_DIA1") or latest("*Dia 1*.csv")
CSV_DIA2 = os.environ.get("CSV_DIA2") or latest("*Dia 2*.csv")
STAMP_BRT = os.environ.get("STAMP_BRT")  # ex.: "2026-06-16 15:00"

if not CSV_DIA1:
    print("ERRO: nenhum CSV 'Dia 1' encontrado (defina CSV_DIA1)", file=sys.stderr)
    sys.exit(1)
if not UNIVERSE.exists():
    print(f"ERRO: universo não encontrado em {UNIVERSE}", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------- carregar CSV
RENAME = {
    "URE": "ure", "Escola": "escola", "Turma": "turma",
    "Bimestre": "bimestre", "DIA_PROVA": "dia_prova",
    "Total_Alunos_Turma": "total_alunos_turma",
    "gabaritos_lidos_cmspp": "gabaritos_lidos_cmspp",
    "Atualizacao": "atualizacao",
    "nome_prova_Roxo": "_np_roxo", "nome_prova_Laranja": "_np_laranja",
    "nome_prova_Verde": "_np_verde", "nome_prova_Amarela": "_np_amarela",
}

SERIE_RE = re.compile(r"^\s*(\d+)")


def derive_serie(np_text):
    if not isinstance(np_text, str) or not np_text:
        return None
    m = SERIE_RE.match(np_text)
    if not m:
        return None
    n = m.group(1)
    return f"{n}EF" if "ano" in np_text.lower() else f"{n}EM"


def load(path, expect_dia):
    print(f"[ler] dia {expect_dia}: {path}")
    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
    print(f"       {len(df):,} linhas brutas")
    keep = [c for c in RENAME if c in df.columns]
    df = df[keep].rename(columns=RENAME)
    before = len(df)
    df = df[df["dia_prova"] == expect_dia]
    if len(df) != before:
        print(f"       filtro dia_prova={expect_dia}: {before:,} -> {len(df):,}")
    return df


t0 = time.time()
parts = [load(CSV_DIA1, 1)]
if CSV_DIA2:
    parts.append(load(CSV_DIA2, 2))
df = pd.concat(parts, ignore_index=True)
print(f"[concat] {len(df):,} linhas")

# serie a partir do primeiro nome_prova não-nulo
np_cols = [c for c in ["_np_roxo", "_np_laranja", "_np_verde", "_np_amarela"] if c in df.columns]
df["_nome_prova"] = df[np_cols].bfill(axis=1).iloc[:, 0] if np_cols else None
df["serie"] = df["_nome_prova"].map(derive_serie)

for c in ["dia_prova", "total_alunos_turma", "gabaritos_lidos_cmspp"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.dropna(subset=["ure", "escola", "turma", "dia_prova"])
# dedup (ure,escola,turma,dia_prova) — mantém a última
key = ["ure", "escola", "turma", "dia_prova"]
dups = int(df.duplicated(subset=key, keep=False).sum())
if dups:
    df = df.drop_duplicates(subset=key, keep="last")
    print(f"[dedup] {dups:,} linhas duplicadas -> {len(df):,}")


def md5(*parts):
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()


df["turma_id"] = [md5(u, e, t) for u, e, t in zip(df["ure"], df["escola"], df["turma"])]
df["lidos_int"] = df["gabaritos_lidos_cmspp"].fillna(0).astype(int)

# leituras do B2 por turma_id (lidos por dia)
reads = {}  # turma_id -> {"d1": x, "d2": y}
for r in df.itertuples(index=False):
    e = reads.setdefault(r.turma_id, {"d1": 0, "d2": 0})
    e["d1" if r.dia_prova == 1 else "d2"] += r.lidos_int

# turmas do B2 (para detectar as que não estão no universo)
b2_turmas = {}
for r in df.itertuples(index=False):
    b2_turmas.setdefault(r.turma_id, {
        "ure": r.ure, "escola": r.escola, "escola_id": md5(r.ure, r.escola),
        "turma": r.turma, "serie": r.serie,
        "alunos": int(r.total_alunos_turma) if pd.notna(r.total_alunos_turma) else 0,
    })

# ---------------------------------------------------------- universo (esperado)
universe = json.loads(UNIVERSE.read_text(encoding="utf-8"))
uni_ids = {u["turma_id"] for u in universe}

# Esperado por turma (denominador):
#   - turma presente no B2  -> usa o esperado do PRÓPRIO B2 (Total_Alunos_Turma)
#   - turma só no universo  -> usa o esperado do B1 (melhor estimativa p/ pendentes)
# Leituras (lidos) sempre vêm do B2 (0 nas turmas ainda sem atividade).
by_id = {u["turma_id"]: {**u, "lidos_d1": 0, "lidos_d2": 0} for u in universe}

for tid, t in b2_turmas.items():
    rd = reads.get(tid, {"d1": 0, "d2": 0})
    if tid in by_id:
        row = by_id[tid]
        row["alunos"] = t["alunos"] or row["alunos"]   # esperado do B2 (B1 se B2 vier 0)
        row["lidos_d1"], row["lidos_d2"] = rd["d1"], rd["d2"]
        if not row.get("serie") and t["serie"]:
            row["serie"] = t["serie"]
    else:
        by_id[tid] = {
            "ure": t["ure"], "escola": t["escola"], "escola_id": t["escola_id"],
            "turma_id": tid, "turma": t["turma"], "serie": t["serie"],
            "alunos": t["alunos"], "lidos_d1": rd["d1"], "lidos_d2": rd["d2"],
        }

pt = pd.DataFrame(list(by_id.values()))
b2_only = [tid for tid in b2_turmas if tid not in uni_ids]
matched = len(b2_turmas) - len(b2_only)
pendentes = len(universe) - matched
print(f"[merge] universo {len(universe):,} | B2 ativas {len(b2_turmas):,} "
      f"(casadas {matched:,} + fora do universo {len(b2_only):,}) | "
      f"pendentes {pendentes:,} | total {len(pt):,}")

# alunos esperados valem para os dois dias (toda turma faz D1 e D2)
pt["alunos"] = pt["alunos"].fillna(0).astype(int)
pt["lidos_d1"] = pt["lidos_d1"].astype(int)
pt["lidos_d2"] = pt["lidos_d2"].astype(int)


def pct(num, den):
    return round(100.0 * num / den, 2) if den else 0


SERIE_ORDER = {"4EF": 1, "5EF": 2, "6EF": 3, "7EF": 4, "8EF": 5, "9EF": 6,
               "1EM": 7, "2EM": 8, "3EM": 9}

# ----------------------------------------------------------------- summary
tot_alunos = int(pt["alunos"].sum())
tot_d1 = int(pt["lidos_d1"].sum())
tot_d2 = int(pt["lidos_d2"].sum())
summary = {
    "total_alunos": tot_alunos,
    "total_lidos_dia1": tot_d1,
    "total_lidos_dia2": tot_d2,
    "perc_dia1": pct(tot_d1, tot_alunos),
    "perc_dia2": pct(tot_d2, tot_alunos),
}

# --------------------------------------------------------- resumo por série
resumo = []
for serie, grp in pt[pt["serie"].notna()].groupby("serie"):
    a = int(grp["alunos"].sum())
    resumo.append({
        "serie": serie, "serie_order": SERIE_ORDER.get(serie, 99),
        "total_alunos": a,
        "lidos_dia1": int(grp["lidos_d1"].sum()),
        "lidos_dia2": int(grp["lidos_d2"].sum()),
        "perc_dia1": pct(int(grp["lidos_d1"].sum()), a),
        "perc_dia2": pct(int(grp["lidos_d2"].sum()), a),
    })
resumo.sort(key=lambda r: r["serie_order"])

# ----------------------------------------------------------- seduc por URE
seduc = []
for ure, grp in pt.groupby("ure"):
    a = int(grp["alunos"].sum())
    seduc.append({
        "ure": ure,
        "total_escolas": int(grp["escola_id"].nunique()),
        "total_turmas": int(grp["turma_id"].nunique()),
        "total_alunos": a,
        "perc_dia1": pct(int(grp["lidos_d1"].sum()), a),
        "perc_dia2": pct(int(grp["lidos_d2"].sum()), a),
    })
seduc.sort(key=lambda r: r["ure"])

# --------------------------------------------------- escolas por URE×escola
escolas = []
for (ure, escola_id), grp in pt.groupby(["ure", "escola_id"]):
    a = int(grp["alunos"].sum())
    escolas.append({
        "ure": ure, "escola_id": escola_id, "escola": grp["escola"].max(),
        "total_turmas": int(grp["turma_id"].nunique()),
        "total_alunos": a,
        "perc_dia1": pct(int(grp["lidos_d1"].sum()), a),
        "perc_dia2": pct(int(grp["lidos_d2"].sum()), a),
    })
escolas.sort(key=lambda r: (r["escola"] or ""))

# --------------------------------------------------------- turmas (lazy)
turmas = []
for r in pt.sort_values("turma").itertuples(index=False):
    turmas.append({
        "escola_id": r.escola_id, "turma_id": r.turma_id, "turma": r.turma,
        "serie": r.serie if pd.notna(r.serie) else None,
        "total_alunos": int(r.alunos),
        "perc_dia1": pct(int(r.lidos_d1), int(r.alunos)),
        "perc_dia2": pct(int(r.lidos_d2), int(r.alunos)),
    })

# ----------------------------------------------------------------- timestamp
if STAMP_BRT:
    atualizacao_iso = STAMP_BRT.strip().replace(" ", "T") + ":00-03:00"
else:
    raw = pd.to_datetime(df["atualizacao"], errors="coerce").max()
    atualizacao_iso = (raw.strftime("%Y-%m-%dT%H:%M:%S") + "-03:00") if pd.notna(raw) else None

# ----------------------------------------------------------------- escrever
bundle = {"atualizacao": atualizacao_iso, "summary": summary,
          "resumo": resumo, "seduc": seduc, "escolas": escolas}
turmas_payload = {"atualizacao": atualizacao_iso, "turmas": turmas}

OUT.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
OUT_TURMAS.write_text(json.dumps(turmas_payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
size_kb = OUT.stat().st_size / 1024
size_turmas_mb = OUT_TURMAS.stat().st_size / 1024 / 1024
print(f"\nOK — bundle.json {size_kb:.0f} KB | turmas.json {size_turmas_mb:.2f} MB "
      f"({len(turmas):,} turmas, {len(escolas):,} escolas, {len(seduc)} UREs) em {time.time()-t0:.1f}s")
print(f"   atualizacao={atualizacao_iso}")
print(f"   total esperado={tot_alunos:,}  lidos D1={tot_d1:,}  %D1={summary['perc_dia1']}  %D2={summary['perc_dia2']}")
