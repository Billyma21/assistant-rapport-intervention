#!/usr/bin/env bash
# Lance l'assistant. Aucune installation prealable n'est necessaire.
cd "$(dirname "$0")" || exit 1
PY=python3
command -v $PY >/dev/null 2>&1 || PY=python
exec $PY app.py
