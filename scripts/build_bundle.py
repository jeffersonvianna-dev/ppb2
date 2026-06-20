"""
Gera public/bundle.json (core) e public/turmas.json (lazy) da Prova Paulista B2.

DENOMINADOR / "total esperado" — dois modos (auto-detectado):

  1) BASE COMPLETA (preferido): o export já traz TODAS as turmas, inclusive as
     pendentes (com leitura 0). Nesse caso o denominador sai 100% do próprio B2
     (coluna Total_Alunos_Turma). Detectado quando o nº de turmas do arquivo é
     próximo do universo (>= 70% de `scripts/universe.json`).

  2) BASE SÓ COM ATIVAS (fallback): exports antigos do B2 só listavam turmas que
     já tinham começado a subir cartões (toda linha com leitura > 0). Aí o total
     ficaria subdimensionado, então hibridizamos: esperado do próprio B2 nas
     turmas presentes + esperado do B1 (`scripts/universe.json`, ~82k turmas /
     2,63 mi) nas pendentes. 99,8% casam por turma_id = md5(ure|escola|turma).

Lê os dois dias (DIA_PROVA 1 e 2) do mesmo CSV. Linhas sem dia válido são lixo
e são descartadas.

Uso:
    python scripts/build_bundle.py
    CSV_DIA1=".../Dia 1-....csv" STAMP_BRT="2026-06-16 17:00" python scripts/build_bundle.py
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


# colunas obrigatórias do relatório de cartões (ignora outros exports, ex.:
# "Provas Realizadas / Média de Nota", que tem outro layout e cai em Downloads)
REQUIRED_COLS = ("DIA_PROVA", "gabaritos_lidos_cmspp")
DIA3_COLS = ("TurmaId", "Provas_Realizadas")  # layout do Dia 3 (prova digital)


def _has_cols(path, cols):
    try:
        with open(path, encoding="utf-8") as fh:
            head = fh.readline()
        return all(c in head for c in cols)
    except Exception:
        return False


def latest(pattern, cols=REQUIRED_COLS):
    hits = sorted(glob.glob(str(DOWNLOADS / pattern)), key=os.path.getmtime, reverse=True)
    for h in hits:                       # mais recente com o layout pedido
        if _has_cols(h, cols):
            return h
    return None


CSV_DIA1 = os.environ.get("CSV_DIA1") or latest("*Dia 1*.csv")
CSV_DIA2 = os.environ.get("CSV_DIA2") or latest("*Dia 2*.csv")
# Dia 3 = prova digital (só 2EM/3EM). Arquivo "Dados Completos-AAAA-MM-DD.csv"
# (sem "Dia" no nome), layout Provas_Realizadas. Casa por TurmaId com a base regular.
CSV_DIA3 = os.environ.get("CSV_DIA3") or latest("Dados Completos-*.csv", DIA3_COLS)
STAMP_BRT = os.environ.get("STAMP_BRT")  # ex.: "2026-06-16 17:00"

if not CSV_DIA1:
    print("ERRO: nenhum CSV 'Dia 1' encontrado (defina CSV_DIA1)", file=sys.stderr)
    sys.exit(1)

# Escolas a EXCLUIR do painel (por escola_id = md5(URE|Municipio|Escola)).
# Pedido Jeff 18/jun: escolas indígenas (aldeias) da URE REGISTRO.
EXCLUDE_ESCOLAS = {
    "be457e56a20a368dde16cb5b25a7945f",  # ALDEIA RIO BRANCO II (REGISTRO/CANANEIA)
    "faab8544d53092ac9c922e9a65189587",  # ALDEIA SANTA CRUZ (REGISTRO/CANANEIA)
    "781d8037ae168ee1e5460d55e63a819f",  # E.E.I. ALDEIA MA'ENDU'A PORÃ (REGISTRO/CANANEIA)
    "5bf9f97a98cfdd97127d9b2c935c15d6",  # ALDEIA PINDO TY (REGISTRO/PARIQUERA-ACU)
    "20f1c42063b6572a9bb2050a6b49718a",  # ALDEIA TAQUARI (REGISTRO/ELDORADO)
    "cb58b0f6848ce45db493bcced1f7b316",  # ALDEIA PEGUAO TY (REGISTRO/SETE BARRAS)
    "73ae3ff2c2715542e9e782608c783320",  # ALDEIA TAKUARI TY (REGISTRO/CANANEIA)
    "a146af0dbff9d4824751a5647d90a8de",  # ALDEIA ARACA MIRIM (REGISTRO/PARIQUERA-ACU)
    "22e97f4e0bd4290c24c287db4225d8f1",  # ALDEIA ITAPU MIRIM (REGISTRO/REGISTRO)
}

# ---------------------------------------------------------------- carregar CSV
RENAME = {
    "URE": "ure", "Municipio": "municipio", "Escola": "escola", "Turma": "turma",
    "TurmaId": "turma_id_src",
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


def load_all(path):
    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
    keep = [c for c in RENAME if c in df.columns]
    df = df[keep].rename(columns=RENAME)
    df["dia_prova"] = pd.to_numeric(df["dia_prova"], errors="coerce")
    n0 = len(df)
    df = df[df["dia_prova"].isin([1, 2])].copy()  # descarta linhas sem dia (lixo)
    print(f"[ler] {os.path.basename(path)}: {n0:,} linhas -> {len(df):,} (dias 1/2)")
    return df


t0 = time.time()
parts = [load_all(CSV_DIA1)]
if CSV_DIA2 and os.path.abspath(CSV_DIA2) != os.path.abspath(CSV_DIA1):
    parts.append(load_all(CSV_DIA2))
df = pd.concat(parts, ignore_index=True)

# serie a partir do primeiro nome_prova não-nulo
np_cols = [c for c in ["_np_roxo", "_np_laranja", "_np_verde", "_np_amarela"] if c in df.columns]
df["_nome_prova"] = df[np_cols].bfill(axis=1).iloc[:, 0] if np_cols else None
df["serie"] = df["_nome_prova"].map(derive_serie)

df["total_alunos_turma"] = pd.to_numeric(df["total_alunos_turma"], errors="coerce")
df["gabaritos_lidos_cmspp"] = pd.to_numeric(df["gabaritos_lidos_cmspp"], errors="coerce")
df["dia_prova"] = df["dia_prova"].astype(int)
df = df.dropna(subset=["ure", "escola", "turma"])


def md5(*parts):
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()


# Identidade da turma = TurmaId REAL do sistema (único) — evita fundir turmas/escolas
# homônimas, que existem (ex.: 2 "1ª A - EM" na mesma escola com TurmaId diferente).
# Escola = md5(URE|Municipio|Escola): não há código de escola na base; o Municipio
# separa escolas homônimas dentro da mesma URE.
mun = df["municipio"].fillna("") if "municipio" in df.columns else pd.Series("", index=df.index)
df["escola_id"] = [md5(u, m, e) for u, m, e in zip(df["ure"], mun, df["escola"])]
if EXCLUDE_ESCOLAS:
    n0 = len(df)
    df = df[~df["escola_id"].isin(EXCLUDE_ESCOLAS)].copy()
    if len(df) != n0:
        print(f"[excluir] {n0 - len(df):,} linhas de escola(s) na lista de exclusão removidas")
# chave por NOME só para casar com o universo do B1 no fallback (universe.json usa md5(URE|Escola|Turma))
df["_namekey"] = [md5(u, e, t) for u, e, t in zip(df["ure"], df["escola"], df["turma"])]
if "turma_id_src" in df.columns:
    tid = pd.to_numeric(df["turma_id_src"], errors="coerce")
    df["turma_id"] = tid.apply(lambda v: str(int(v)) if pd.notna(v) else None)
    faltam = df["turma_id"].isna()
    if faltam.any():  # fallback raro: TurmaId nulo -> usa md5 dos nomes
        df.loc[faltam, "turma_id"] = df.loc[faltam, "_namekey"]
        print(f"[aviso] {int(faltam.sum()):,} linhas sem TurmaId -> usei md5 dos nomes")
else:
    df["turma_id"] = df["_namekey"]

# dedup por (turma_id, dia_prova) — NÃO por nome, p/ não fundir homônimas
key = ["turma_id", "dia_prova"]
dups = int(df.duplicated(subset=key, keep=False).sum())
if dups:
    df = df.drop_duplicates(subset=key, keep="last")
    print(f"[dedup] {dups:,} linhas duplicadas removidas -> {len(df):,}")

df["_alunos"] = df["total_alunos_turma"].fillna(0).astype(int)
lidos = df["gabaritos_lidos_cmspp"].fillna(0).astype(int)
df["_l1"] = lidos.where(df["dia_prova"] == 1, 0)
df["_l2"] = lidos.where(df["dia_prova"] == 2, 0)

# --------------------------------------------------- agregação por turma (B2)
# Agrupa SÓ por turma_id (TurmaId é único por turma). Não inclui escola_id na chave:
# evita que variações de grafia de escola/município entre os arquivos do dia 1 e dia 2
# quebrem a mesma turma em dois grupos (e separem D1 de D2).
por = df.groupby("turma_id", sort=False).agg(
    ure=("ure", "max"),
    escola_id=("escola_id", "max"),
    escola=("escola", "max"),
    turma=("turma", "max"),
    serie=("serie", "max"),
    namekey=("_namekey", "max"),     # p/ casar com B1 no fallback
    alunos=("_alunos", "max"),       # mesmo aluno serve aos dois dias
    lidos_d1=("_l1", "sum"),
    lidos_d2=("_l2", "sum"),
).reset_index()

# ------------------------------------------------------ modo do denominador
universe = json.loads(UNIVERSE.read_text(encoding="utf-8")) if UNIVERSE.exists() else []
uni_size = len(universe) or 82000
base_completa = len(por) >= 0.70 * uni_size

if base_completa:
    pt = por.copy()
    print(f"[modo] BASE COMPLETA — denominador 100% do B2 ({len(pt):,} turmas)")
else:
    # fallback híbrido: universo do B1 + leituras/esperado do B2 onde houver
    uni_ids = {u["turma_id"] for u in universe}   # ids do B1 = md5(URE|Escola|Turma)
    by_id = {u["turma_id"]: {**u, "lidos_d1": 0, "lidos_d2": 0} for u in universe}
    for r in por.itertuples(index=False):
        if r.namekey in by_id:   # casa pelo nome (esquema de id do B1)
            row = by_id[r.namekey]
            row["alunos"] = int(r.alunos) or row["alunos"]
            row["lidos_d1"], row["lidos_d2"] = int(r.lidos_d1), int(r.lidos_d2)
            if not row.get("serie") and pd.notna(r.serie):
                row["serie"] = r.serie
        else:
            by_id[r.turma_id] = {
                "ure": r.ure, "escola": r.escola, "escola_id": r.escola_id,
                "turma_id": r.turma_id, "turma": r.turma,
                "serie": r.serie if pd.notna(r.serie) else None,
                "alunos": int(r.alunos), "lidos_d1": int(r.lidos_d1), "lidos_d2": int(r.lidos_d2),
            }
    pt = pd.DataFrame(list(by_id.values()))
    b2_only = sum(1 for r in por.itertuples(index=False) if r.namekey not in uni_ids)
    print(f"[modo] HÍBRIDO (base só com ativas) — B2 {len(por):,} "
          f"(+{b2_only} fora do universo) sobre universo B1 {len(universe):,}")

pt["alunos"] = pt["alunos"].fillna(0).astype(int)
pt["lidos_d1"] = pt["lidos_d1"].astype(int)
pt["lidos_d2"] = pt["lidos_d2"].astype(int)

# ------------------------------------------------ Dia 3 (prova digital, 2EM/3EM)
# Casa por TurmaId com a base regular (100% de overlap). Só 2EM/3EM têm Dia 3 —
# nas demais séries o % Dia 3 fica nulo (N/A). Denominador = alunos das turmas de Dia 3.
d3_reads, d3_ids = {}, set()
if CSV_DIA3 and os.path.exists(CSV_DIA3):
    d3 = pd.read_csv(CSV_DIA3, encoding="utf-8", low_memory=False)
    d3["tid"] = pd.to_numeric(d3["TurmaId"], errors="coerce")
    d3 = d3.dropna(subset=["tid"]).copy()
    d3["tid"] = d3["tid"].astype("int64").astype(str)
    d3["pr"] = pd.to_numeric(d3["Provas_Realizadas"], errors="coerce").fillna(0).astype(int)
    d3 = d3.drop_duplicates(subset=["tid"], keep="last")
    d3_reads = dict(zip(d3["tid"], d3["pr"]))
    d3_ids = set(d3_reads)
    print(f"[dia3] {os.path.basename(CSV_DIA3)}: {len(d3_ids):,} turmas | provas={sum(d3_reads.values()):,}")

pt["lidos_d3"] = pt["turma_id"].map(d3_reads).fillna(0).astype(int)
pt["tem_d3"] = pt["turma_id"].isin(d3_ids)
pt["alunos_d3"] = pt["alunos"].where(pt["tem_d3"], 0)


def pct(num, den):
    # trava em 100% (há turmas com matrícula subdimensionada na fonte que leem >100%)
    return round(min(100.0, 100.0 * num / den), 2) if den else 0


def pct_n(num, den):
    # como pct, mas retorna None (N/A) quando não há denominador (ex.: série sem Dia 3)
    return round(min(100.0, 100.0 * num / den), 2) if den else None


SERIE_ORDER = {"4EF": 1, "5EF": 2, "6EF": 3, "7EF": 4, "8EF": 5, "9EF": 6,
               "1EM": 7, "2EM": 8, "3EM": 9}

# ----------------------------------------------------------------- summary
tot_alunos = int(pt["alunos"].sum())
tot_d1 = int(pt["lidos_d1"].sum())
tot_d2 = int(pt["lidos_d2"].sum())
tot_d3 = int(pt["lidos_d3"].sum())
tot_a3 = int(pt["alunos_d3"].sum())
summary = {
    "total_alunos": tot_alunos,
    "total_lidos_dia1": tot_d1,
    "total_lidos_dia2": tot_d2,
    "total_lidos_dia3": tot_d3,
    "total_alunos_dia3": tot_a3,
    "perc_dia1": pct(tot_d1, tot_alunos),
    "perc_dia2": pct(tot_d2, tot_alunos),
    "perc_dia3": pct_n(tot_d3, tot_a3),
}

# --------------------------------------------------------- resumo por série
resumo = []
for serie, grp in pt[pt["serie"].notna()].groupby("serie"):
    a = int(grp["alunos"].sum())
    l3, a3 = int(grp["lidos_d3"].sum()), int(grp["alunos_d3"].sum())
    resumo.append({
        "serie": serie, "serie_order": SERIE_ORDER.get(serie, 99),
        "total_alunos": a,
        "lidos_dia1": int(grp["lidos_d1"].sum()),
        "lidos_dia2": int(grp["lidos_d2"].sum()),
        "lidos_dia3": l3 if a3 else None,
        "perc_dia1": pct(int(grp["lidos_d1"].sum()), a),
        "perc_dia2": pct(int(grp["lidos_d2"].sum()), a),
        "perc_dia3": pct_n(l3, a3),
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
        "perc_dia3": pct_n(int(grp["lidos_d3"].sum()), int(grp["alunos_d3"].sum())),
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
        "perc_dia3": pct_n(int(grp["lidos_d3"].sum()), int(grp["alunos_d3"].sum())),
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
        "perc_dia3": pct_n(int(r.lidos_d3), int(r.alunos)) if r.tem_d3 else None,
    })

# ----------------------------------------------------------------- timestamp
if STAMP_BRT:
    atualizacao_iso = STAMP_BRT.strip().replace(" ", "T") + ":00-03:00"
else:
    raw = pd.to_datetime(df["atualizacao"], errors="coerce", utc=True).max()
    atualizacao_iso = raw.tz_convert("America/Sao_Paulo").isoformat() if pd.notna(raw) else None

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
print(f"   total esperado={tot_alunos:,}  %D1={summary['perc_dia1']}  %D2={summary['perc_dia2']}  "
      f"%D3={summary['perc_dia3']} (D3 esperado={tot_a3:,}, lidos={tot_d3:,})")
