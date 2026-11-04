#!/usr/bin/env bash
# Tum kalite kapilari tek komutta: sir taramasi, ruff, mypy, testler + kapsama,
# CLI duman testi. Adimlardan biri kirmizi olursa betik kirmizi biter.
#
# Kullanim:  bash scripts/check.sh
# Python secimi: PYTHON ortam degiskeni > .venv > python3 > python.

set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
    for aday in ".venv/Scripts/python.exe" ".venv/bin/python" "python3" "python"; do
        if [ -x "$aday" ] || command -v "$aday" >/dev/null 2>&1; then
            PYTHON="$aday"
            break
        fi
    done
fi

if [ -z "$PYTHON" ]; then
    echo "HATA: python yorumlayicisi bulunamadi (PYTHON=... ile verin)" >&2
    exit 127
fi

echo "== ortam =="
"$PYTHON" -V || exit 127
"$PYTHON" - <<'PY' || exit 1
import sys
if sys.version_info < (3, 10):
    print("HATA: Python >= 3.10 gerekli", file=sys.stderr)
    raise SystemExit(1)
PY

BASARISIZ=0
SON_ADIM=""

adim() {
    ad="$1"
    shift
    SON_ADIM="$ad"
    echo
    echo "== $ad =="
    if "$@"; then
        echo "-- $ad: GECTI"
    else
        echo "-- $ad: BASARISIZ" >&2
        BASARISIZ=1
    fi
}

adim "sir taramasi" "$PYTHON" scripts/sir_tara.py
adim "ruff (lint)" "$PYTHON" -m ruff check .
adim "ruff (bicim)" "$PYTHON" -m ruff format --check .
adim "mypy (tip kontrolu)" "$PYTHON" -m mypy
adim "pytest + kapsama (>=%85)" "$PYTHON" -m pytest --cov --cov-report=term-missing

echo
echo "== CLI duman testi =="
if PYTHONPATH=src "$PYTHON" -m rg_fihrist --surum; then
    echo "-- CLI duman testi: GECTI"
else
    echo "-- CLI duman testi: BASARISIZ" >&2
    BASARISIZ=1
fi

echo
if [ "$BASARISIZ" -ne 0 ]; then
    echo "SONUC: BASARISIZ (son adim: $SON_ADIM). Ayrintilar yukarida." >&2
    exit 1
fi

echo "SONUC: TUM KONTROLLER GECTI (check=0)"
exit 0
