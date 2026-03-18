#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

LOOPS="${1:-1}"
if ! [[ "$LOOPS" =~ ^[0-9]+$ ]] || [[ "$LOOPS" -lt 1 ]]; then
  echo "Uso: ./run_tests.sh [loops>=1]"
  exit 1
fi

echo "[1/2] Ejecutando suite completa..."
python3 -m unittest discover -s tests -p 'test_*.py' -v

echo "[2/2] Repetición de escenarios extremos (${LOOPS} veces)..."
for ((i=1; i<=LOOPS; i++)); do
  echo "  - Iteración ${i}/${LOOPS}"
  python3 -m unittest tests.test_extreme_scenarios.TestExtremeScenarios -v
done

echo "Pruebas completadas correctamente."
