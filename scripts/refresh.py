"""
Pipeline de atualização (várias vezes/dia) do ppb2 — SEM Supabase.

Lê o(s) CSV(s) mais recente(s) de Downloads, regera o bundle estático e
faz commit + push (dispara o deploy automático no Vercel).

Uso:
    python scripts/refresh.py
    # força rerun mesmo sem mudança nos CSVs:
    FORCE=1 python scripts/refresh.py
    # sobrescreve o timestamp do header:
    STAMP_BRT="2026-06-16 15:00" python scripts/refresh.py

Faz:
  0. Sai cedo se o CSV de entrada não mudou (evita commit vazio).
  1. python scripts/build_bundle.py   (CSV -> public/bundle.json + turmas.json)
  2. git add public/*.json + commit + push
"""
import glob
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / ".refresh-state.json"
DOWNLOADS = Path(os.path.expanduser("~")) / "Downloads"


def latest(pattern):
    hits = sorted(glob.glob(str(DOWNLOADS / pattern)), key=os.path.getmtime)
    return hits[-1] if hits else None


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, **kw):
    print(f"\n$ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    r = subprocess.run(cmd, cwd=ROOT, **kw)
    if r.returncode != 0:
        sys.exit(r.returncode)
    return r


csv_d1 = os.environ.get("CSV_DIA1") or latest("*Dia 1*.csv")
csv_d2 = os.environ.get("CSV_DIA2") or latest("*Dia 2*.csv")

# 0. Sai cedo se os CSVs não mudaram
state_now = {
    "csv_dia1": file_hash(csv_d1) if csv_d1 and Path(csv_d1).exists() else None,
    "csv_dia2": file_hash(csv_d2) if csv_d2 and Path(csv_d2).exists() else None,
    "stamp": os.environ.get("STAMP_BRT"),
}
if not os.environ.get("FORCE") and STATE_FILE.exists() and state_now["csv_dia1"]:
    try:
        if json.loads(STATE_FILE.read_text()) == state_now:
            print("[skip] CSVs inalterados desde o último refresh (use FORCE=1 para rodar mesmo assim).")
            sys.exit(0)
    except json.JSONDecodeError:
        pass

# 1. Gera bundle estático direto do CSV
run([sys.executable, "scripts/build_bundle.py"])

# 2. Persiste estado para o próximo run
STATE_FILE.write_text(json.dumps(state_now, indent=2))

# 3. Commit + push (dispara deploy automático no Vercel)
run(["git", "add", "public/bundle.json", "public/turmas.json"])
diff = subprocess.run(["git", "diff", "--cached", "--quiet", "public/bundle.json", "public/turmas.json"], cwd=ROOT)
if diff.returncode == 0:
    print("\n[skip] bundle sem mudanças, nada para commitar.")
    sys.exit(0)

import datetime as dt
ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
run([
    "git", "-c", "user.email=jefferson.vianna.dev@gmail.com",
    "-c", "user.name=Jefferson Vianna",
    "commit", "-m", f"data: refresh bundle {ts}"
])
run(["git", "push"])
print("\n✓ refresh concluído — Vercel deploy em ~30s, CDN em ≤5min")
