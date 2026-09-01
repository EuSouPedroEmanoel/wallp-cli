#!/usr/bin/env bash
# wallp-cli — instalador remoto (para curl | bash)
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallp-cli/master/quick-install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallp-cli/master/quick-install.sh | bash -s -- -y
#   bash <(curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallp-cli/master/quick-install.sh) --check
set -euo pipefail
REPO="https://github.com/EuSouPedroEmanoel/wallp-cli.git"
TARGET="${WALLP_CLI_DIR:-$HOME/dev/wallp/wallp-cli}"
BRANCH="${WALLP_BRANCH:-master}"
ARGS=("$@")

# se já estamos dentro de um clone válido, só delega
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
if [ -f "$SCRIPT_DIR/install.sh" ] && [ -d "$SCRIPT_DIR/src/wallp" ]; then
  exec "$SCRIPT_DIR/install.sh" "${ARGS[@]}"
fi

have() { command -v "$1" >/dev/null 2>&1; }

if ! have git; then
  echo "erro: git não encontrado (pacote git)" >&2
  exit 1
fi

if [ -d "$TARGET/.git" ]; then
  echo "==> Atualizando $TARGET ($BRANCH)..."
  git -C "$TARGET" fetch --quiet origin "$BRANCH" || true
  # tenta fast-forward, se falhar rebaseia
  git -C "$TARGET" checkout -q "$BRANCH" 2>/dev/null || git -C "$TARGET" checkout -q master 2>/dev/null || true
  git -C "$TARGET" pull --ff-only --quiet 2>/dev/null || git -C "$TARGET" pull --rebase --quiet 2>/dev/null || true
else
  echo "==> Clonando wallp-cli em $TARGET..."
  mkdir -p "$(dirname "$TARGET")"
  git clone --branch "$BRANCH" --depth 1 "$REPO" "$TARGET" 2>&1 | sed 's/^/  /'
fi

exec "$TARGET/install.sh" "${ARGS[@]}"
