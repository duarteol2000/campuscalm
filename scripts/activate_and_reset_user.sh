#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/activate_and_reset_user.sh <email> [nova_senha]

Exemplos:
  ./scripts/activate_and_reset_user.sh lorenacibelly745@gmail.com Teste@1234
  ./scripts/activate_and_reset_user.sh lorenacibelly745@gmail.com

Se a senha nao for informada, o script pede interativamente.
O script:
  1) ativa a conta (is_active=True)
  2) redefine a senha informada
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

if [ $# -lt 1 ]; then
  usage
  exit 1
fi

EMAIL="$1"
PASSWORD="${2:-}"

if [ -z "$PASSWORD" ]; then
  read -r -s -p "Nova senha para ${EMAIL}: " PASSWORD
  echo
  read -r -s -p "Confirme a senha: " PASSWORD_CONFIRM
  echo
  if [ "$PASSWORD" != "$PASSWORD_CONFIRM" ]; then
    echo "Erro: as senhas nao conferem."
    exit 1
  fi
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

if [ ! -f "manage.py" ]; then
  echo "Erro: execute este script dentro do projeto (manage.py nao encontrado)."
  exit 1
fi

if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Erro: Python nao encontrado."
  exit 1
fi

echo "Usando Python: $PYTHON_BIN"

CC_USER_EMAIL="$EMAIL" CC_USER_PASSWORD="$PASSWORD" "$PYTHON_BIN" manage.py shell -c "
import os
import sys
from django.contrib.auth import get_user_model

email = os.environ.get('CC_USER_EMAIL', '').strip().lower()
password = os.environ.get('CC_USER_PASSWORD', '')

if not email:
    print('Erro: email vazio.')
    sys.exit(2)
if not password:
    print('Erro: senha vazia.')
    sys.exit(2)

User = get_user_model()
user = User.objects.filter(email__iexact=email).first()
if not user:
    print(f'Erro: usuario nao encontrado para email={email}')
    sys.exit(1)

before = user.is_active
user.is_active = True
user.set_password(password)
user.save(update_fields=['is_active', 'password'])
user.refresh_from_db(fields=['is_active'])

print(f'OK: usuario={user.email} before_is_active={before} after_is_active={user.is_active}')
print('Senha redefinida com sucesso.')
"

echo "Concluido."
