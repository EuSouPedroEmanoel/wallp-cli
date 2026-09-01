#!/usr/bin/env bash
# wallp-cli — instalador remoto (para curl | bash)
# Sempre aponta para a última release estável por padrão (tarball), com suporte a --version.
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallp-cli/master/quick-install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallp-cli/master/quick-install.sh | bash -s -- -y
#   curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallp-cli/master/quick-install.sh | bash -s -- --version 1.0.0
#   curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallp-cli/master/quick-install.sh | bash -s -- --version 1.0.0 --git
#   WALLP_VERSION=1.0.0 bash quick-install.sh -y
#   WALLP_VERSION=v1.0.0 bash quick-install.sh --git -y
#   bash <(curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallp-cli/master/quick-install.sh) --check
# Flags:
#   --version <ver>  versão específica (ex.: 1.0.0, v1.0.0, latest, master, feat/native-backend)
#   --git            força git clone --branch (útil para branches, permite git pull depois)
#   --help           mostra ajuda
# Env:
#   WALLP_VERSION, WALLP_CLI_DIR, WALLP_BRANCH
set -euo pipefail
REPO="https://github.com/EuSouPedroEmanoel/wallp-cli.git"
TARGET="${WALLP_CLI_DIR:-$HOME/dev/wallp/wallp-cli}"
BRANCH_FALLBACK="${WALLP_BRANCH:-master}"

VERSION="${WALLP_VERSION:-}"
USE_GIT=0
INSTALL_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="$2"; shift 2 ;;
    --version=*)
      VERSION="${1#--version=}"; shift ;;
    --git)
      USE_GIT=1; shift ;;
    --help|-h)
      echo "uso: $0 [--version <ver>] [--git] [--check] [-y]"
      echo "  --version  versão (1.0.0, v1.0.0, latest, master, feat/native-backend)"
      echo "  --git      usa git clone --branch em vez de tarball (permite git pull)"
      echo "  env WALLP_VERSION, WALLP_CLI_DIR, WALLP_BRANCH"
      exit 0 ;;
    *)
      INSTALL_ARGS+=("$1"); shift ;;
  esac
done

have() { command -v "$1" >/dev/null 2>&1; }

# se já estamos dentro de um clone válido e sem --version, só delega
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
if [ -z "$VERSION" ] && [ "$USE_GIT" -eq 0 ] && [ -f "$SCRIPT_DIR/install.sh" ] && [ -d "$SCRIPT_DIR/src/wallp" ]; then
  exec "$SCRIPT_DIR/install.sh" "${INSTALL_ARGS[@]}"
fi

# normaliza versão e resolve latest
resolve_latest_tag() {
  local tag=""
  if have curl; then
    tag=$(curl -fsSL https://api.github.com/repos/EuSouPedroEmanoel/wallp-cli/releases/latest 2>/dev/null | grep -o '"tag_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || true)
  fi
  if [ -z "$tag" ] && have wget; then
    tag=$(wget -qO- https://api.github.com/repos/EuSouPedroEmanoel/wallp-cli/releases/latest 2>/dev/null | grep -o '"tag_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || true)
  fi
  echo "$tag"
}

if [ -z "$VERSION" ]; then
  VERSION="$(resolve_latest_tag)"
  if [ -z "$VERSION" ]; then
    VERSION="$BRANCH_FALLBACK"
  fi
fi

# normaliza v prefix
VER_RAW="$VERSION"
VERSION_NOV="${VERSION#v}"
TAG="v${VERSION_NOV}"

# decide se é branch (master, feat/*, etc.) ou release version (X.Y.Z)
is_branch=0
if [[ "$VERSION" == "master" || "$VERSION" == "main" || "$VERSION" == "latest" || "$VERSION" == feat/* ]]; then
  is_branch=1
elif [[ "$VERSION_NOV" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  is_branch=0
else
  # fallback: se contém / ou não parece semver, trata como branch
  if [[ "$VERSION" == *"/"* ]]; then
    is_branch=1
  fi
fi

# latest sem tag resolvida vira master fallback já tratado acima
if [ "$VERSION" = "latest" ]; then
  # já resolvemos para tag, mas se falhou api, is_branch já 1 e TAG ainda latest
  if [[ "$TAG" == "vlatest" ]]; then
    is_branch=1
    VERSION="master"
    TAG="master"
  fi
fi

# se pediu git ou é branch, usa git
if [ "$USE_GIT" -eq 1 ] || [ "$is_branch" -eq 1 ]; then
  if ! have git; then
    echo "erro: git não encontrado (pacote git) — use tarball sem --git ou instale git" >&2
    exit 1
  fi
  GIT_BRANCH="$VERSION"
  # se VERSION era semver, usa TAG
  if [ "$is_branch" -eq 0 ]; then
    GIT_BRANCH="$TAG"
  fi
  if [ -d "$TARGET/.git" ]; then
    echo "==> Atualizando $TARGET ($GIT_BRANCH) via git..."
    git -C "$TARGET" fetch --quiet origin "$GIT_BRANCH" 2>/dev/null || git -C "$TARGET" fetch --quiet origin 2>/dev/null || true
    git -C "$TARGET" checkout -q "$GIT_BRANCH" 2>/dev/null || git -C "$TARGET" checkout -q master 2>/dev/null || true
    git -C "$TARGET" pull --ff-only --quiet 2>/dev/null || git -C "$TARGET" pull --rebase --quiet 2>/dev/null || true
  else
    echo "==> Clonando wallp-cli $GIT_BRANCH em $TARGET via git..."
    mkdir -p "$(dirname "$TARGET")"
    git clone --branch "$GIT_BRANCH" --depth 1 "$REPO" "$TARGET" 2>&1 | sed 's/^/  /' || {
      echo "falha no git clone de $GIT_BRANCH, tentando master..." >&2
      git clone --depth 1 "$REPO" "$TARGET" 2>&1 | sed 's/^/  /'
    }
  fi
  exec "$TARGET/install.sh" "${INSTALL_ARGS[@]}"
fi

# modo tarball (padrão, sem git, sem jq) — baixa release
ASSET_VER="$VERSION_NOV"
TARBALL_URL="https://github.com/EuSouPedroEmanoel/wallp-cli/releases/download/$TAG/wallp-cli-$ASSET_VER.tar.gz"
ZIP_URL="https://github.com/EuSouPedroEmanoel/wallp-cli/releases/download/$TAG/wallp-cli-$ASSET_VER.zip"

echo "==> Baixando wallp-cli $TAG via tarball..."
TMPDIR="$(mktemp -d)"
cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

DL_OK=0
if have curl; then
  if curl -fsSL "$TARBALL_URL" -o "$TMPDIR/wallp.tar.gz" 2>/dev/null; then
    DL_OK=1
  elif curl -fsSL "$ZIP_URL" -o "$TMPDIR/wallp.zip" 2>/dev/null; then
    # fallback zip se tar.gz não existir (ex.: conexão)
    if have unzip; then
      echo "  extraindo zip $ASSET_VER..."
      unzip -q "$TMPDIR/wallp.zip" -d "$TMPDIR"
      DL_OK=2
    fi
  fi
elif have wget; then
  if wget -qO "$TMPDIR/wallp.tar.gz" "$TARBALL_URL" 2>/dev/null; then
    DL_OK=1
  elif wget -qO "$TMPDIR/wallp.zip" "$ZIP_URL" 2>/dev/null && have unzip; then
    unzip -q "$TMPDIR/wallp.zip" -d "$TMPDIR"
    DL_OK=2
  fi
else
  echo "erro: curl ou wget necessário para modo tarball (ou use --git)" >&2
  exit 1
fi

if [ "$DL_OK" -eq 0 ]; then
  echo "erro: falha ao baixar $TARBALL_URL" >&2
  echo "tente --git ou verifique a versão em https://github.com/EuSouPedroEmanoel/wallp-cli/releases" >&2
  exit 1
fi

if [ "$DL_OK" -eq 1 ]; then
  echo "  extraindo tar.gz $ASSET_VER..."
  mkdir -p "$TMPDIR/extract"
  tar xzf "$TMPDIR/wallp.tar.gz" -C "$TMPDIR/extract" --strip-components=1 2>/dev/null || tar xzf "$TMPDIR/wallp.tar.gz" -C "$TMPDIR/extract" 2>/dev/null
  EXTRACTED="$TMPDIR/extract"
else
  EXTRACTED="$(find "$TMPDIR" -maxdepth 2 -name "wallp-cli-*" -type d | head -n1)"
  if [ -z "$EXTRACTED" ]; then
    EXTRACTED="$TMPDIR"
  fi
fi

echo "  instalando em $TARGET..."
mkdir -p "$(dirname "$TARGET")"
# preserva .git se existir e for tarball (para não perder histórico quando já clonado)
if [ -d "$TARGET/.git" ] && [ "$DL_OK" -eq 1 ]; then
  # backup .git
  cp -a "$TARGET/.git" "$TMPDIR/git.bak" 2>/dev/null || true
  rm -rf "$TARGET"
  mkdir -p "$TARGET"
  cp -a "$EXTRACTED"/. "$TARGET"/
  if [ -d "$TMPDIR/git.bak" ]; then
    rm -rf "$TARGET/.git"
    mv "$TMPDIR/git.bak" "$TARGET/.git"
  fi
else
  rm -rf "$TARGET"
  mkdir -p "$TARGET"
  cp -a "$EXTRACTED"/. "$TARGET"/
fi

exec "$TARGET/install.sh" "${INSTALL_ARGS[@]}"
