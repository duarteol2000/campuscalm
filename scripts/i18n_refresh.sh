#!/usr/bin/env bash
set -euo pipefail

if ! command -v msguniq >/dev/null 2>&1 || ! command -v msgfmt >/dev/null 2>&1; then
  echo "GNU gettext tools (msguniq/msgfmt) not found. Install gettext and re-run."
  exit 1
fi

python3 manage.py makemessages -l en -l pt_BR -l pt_PT
python3 manage.py compilemessages
