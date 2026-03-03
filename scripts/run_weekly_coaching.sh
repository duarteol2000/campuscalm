#!/usr/bin/env bash
set -euo pipefail

# Bloco: Resolucao de caminho do projeto (script pode ser chamado de qualquer lugar)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/coaching_cron.log"

mkdir -p "${LOG_DIR}"

# Bloco: Header de execucao com timestamp para facilitar auditoria do cron
{
  echo "================================================================"
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] run_weekly_coaching start"
  echo "project=${PROJECT_DIR}"
} >> "${LOG_FILE}"

cd "${PROJECT_DIR}"

# Bloco: Ativacao opcional do ambiente virtual local
if [[ -f "${PROJECT_DIR}/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${PROJECT_DIR}/.venv/bin/activate"
fi

# Bloco: Interpretador Python (venv preferencial, fallback para python3)
if [[ -x "${PROJECT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "ERRO: python3 nao encontrado." >> "${LOG_FILE}"
  exit 1
fi

# Bloco: Modo de execucao
# Uso:
#   scripts/run_weekly_coaching.sh
#   scripts/run_weekly_coaching.sh --user-email aluno@exemplo.com
#   COACH_TEST_EMAIL=aluno@exemplo.com scripts/run_weekly_coaching.sh
if [[ "${1:-}" == "--user-email" && -n "${2:-}" ]]; then
  TARGET_EMAIL="${2}"
elif [[ -n "${COACH_TEST_EMAIL:-}" ]]; then
  TARGET_EMAIL="${COACH_TEST_EMAIL}"
else
  TARGET_EMAIL=""
fi

if [[ -n "${TARGET_EMAIL}" ]]; then
  echo "modo=test user_email=${TARGET_EMAIL}" >> "${LOG_FILE}"
  "${PYTHON_BIN}" manage.py run_weekly_coaching --user-email "${TARGET_EMAIL}" >> "${LOG_FILE}" 2>&1
else
  echo "modo=global" >> "${LOG_FILE}"
  "${PYTHON_BIN}" manage.py run_weekly_coaching >> "${LOG_FILE}" 2>&1
fi

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] run_weekly_coaching end"
  echo
} >> "${LOG_FILE}"

