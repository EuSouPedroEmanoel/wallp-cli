#!/usr/bin/env bash
# wallpha-cli — instalador remoto (para curl | bash)
# Sempre aponta para a última release estável por padrão (tarball), com suporte a --version.
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallpha-cli/master/quick-install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallpha-cli/master/quick-install.sh | bash -s -- -y
#   curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallpha-cli/master/quick-install.sh | bash -s -- --version 1.0.0
#   curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallpha-cli/master/quick-install.sh | bash -s -- --version 1.0.0 --git
#   curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallpha-cli/master/quick-install.sh | bash -s -- --bin
#   curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallpha-cli/master/quick-install.sh | bash -s -- --bin --version 1.0.3
#   WALLPHA_VERSION=1.0.0 bash quick-install.sh -y
#   WALLPHA_VERSION=v1.0.0 bash quick-install.sh --git -y
#   bash <(curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallpha-cli/master/quick-install.sh) --check
# Flags:
#   --version <ver>  versão específica (ex.: 1.0.0, v1.0.0, latest, master, feat/native-backend)
#   --git            força git clone --branch (útil para branches, permite git pull depois)
#   --dev            instala em ~/dev/wallpha/wallpha-cli (dev) — padrão é ~/.local/share/wallpha
#   --bin            pacote mínimo wallpha-cli-bin: sem capa, sem repo dev, wallpaper de ~/Imagens
#   --help           mostra ajuda
# Env:
#   WALLPHA_VERSION, WALLPHA_CLI_DIR, WALLPHA_BRANCH, XDG_DATA_HOME
set -euo pipefail
REPO="https://github.com/EuSouPedroEmanoel/wallpha-cli.git"
# TARGET: dev (~/dev/wallpha/wallpha-cli) com --dev, senão XDG_DATA_HOME (~/.local/share/wallpha) — sem deixar nada em ~/dev
XDG_DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
WALLPHA_DATA_DEFAULT="$XDG_DATA/wallpha"
DEV_TARGET="$HOME/dev/wallpha/wallpha-cli"
BRANCH_FALLBACK="${WALLPHA_BRANCH:-master}"

VERSION="${WALLPHA_VERSION:-}"
USE_GIT=0
DEV_MODE=0
BIN_MODE=0
INSTALL_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="$2"; shift 2 ;;
    --version=*)
      VERSION="${1#--version=}"; shift ;;
    --git)
      USE_GIT=1; shift ;;
    --dev)
      DEV_MODE=1; shift ;;
    --bin)
      BIN_MODE=1; shift ;;
    --help|-h)
      echo "uso: $0 [--version <ver>] [--git] [--dev] [--bin] [--check] [-y]"
      echo "  --version  versão (1.0.0, v1.0.0, latest, master, feat/native-backend)"
      echo "  --git      usa git clone --branch em vez de tarball (permite git pull)"
      echo "  --dev      instala em ~/dev/wallpha/wallpha-cli (dev) — padrão é ~/.local/share/wallpha"
      echo "  --bin      pacote mínimo wallpha-cli-bin: sem capa, wallpaper de ~/Imagens"
      echo "  env WALLPHA_VERSION, WALLPHA_CLI_DIR, WALLPHA_BRANCH, XDG_DATA_HOME"
      exit 0 ;;
    *)
      INSTALL_ARGS+=("$1"); shift ;;
  esac
done

# TARGET respeita WALLPHA_CLI_DIR se usuário exportou, senão escolhe dev vs XDG
if [ -n "${WALLPHA_CLI_DIR:-}" ]; then
  TARGET="$WALLPHA_CLI_DIR"
elif [ "$DEV_MODE" -eq 1 ]; then
  TARGET="$DEV_TARGET"
else
  TARGET="$WALLPHA_DATA_DEFAULT"
fi
# propaga --dev/--bin para install.sh somente se ele suporta (compat com tarballs antigos v1.0.2)
if [ "$DEV_MODE" -eq 1 ]; then
  WANTS_DEV=1
else
  WANTS_DEV=0
fi
if [ "$BIN_MODE" -eq 1 ]; then
  WANTS_BIN=1
else
  WANTS_BIN=0
fi

have() { command -v "$1" >/dev/null 2>&1; }

# se já estamos dentro de um clone válido e sem --version, só delega
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE:-}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
fi
if [ -z "$VERSION" ] && [ "$USE_GIT" -eq 0 ] && [ "$WANTS_DEV" -eq 0 ] && [ "$WANTS_BIN" -eq 0 ] && [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/install.sh" ] && [ -d "$SCRIPT_DIR/src/wallpha" ]; then
  exec "$SCRIPT_DIR/install.sh" "${INSTALL_ARGS[@]}"
fi
if [ -z "$VERSION" ] && [ "$USE_GIT" -eq 0 ] && [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/install.sh" ] && [ -d "$SCRIPT_DIR/src/wallpha" ]; then
  if [ "$WANTS_DEV" -eq 1 ] && grep -q -- "--dev" "$SCRIPT_DIR/install.sh" 2>/dev/null; then
    if [ "$WANTS_BIN" -eq 1 ] && grep -q -- "--bin" "$SCRIPT_DIR/install.sh" 2>/dev/null; then
      exec "$SCRIPT_DIR/install.sh" --dev --bin "${INSTALL_ARGS[@]}"
    else
      exec "$SCRIPT_DIR/install.sh" --dev "${INSTALL_ARGS[@]}"
    fi
  elif [ "$WANTS_BIN" -eq 1 ] && grep -q -- "--bin" "$SCRIPT_DIR/install.sh" 2>/dev/null; then
    exec "$SCRIPT_DIR/install.sh" --bin "${INSTALL_ARGS[@]}"
  fi
fi

# normaliza versão e resolve latest
resolve_latest_tag() {
  local tag=""
  if have curl; then
    tag=$(curl -fsSL https://api.github.com/repos/EuSouPedroEmanoel/wallpha-cli/releases/latest 2>/dev/null | grep -o '"tag_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || true)
  fi
  if [ -z "$tag" ] && have wget; then
    tag=$(wget -qO- https://api.github.com/repos/EuSouPedroEmanoel/wallpha-cli/releases/latest 2>/dev/null | grep -o '"tag_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || true)
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
    echo "==> Clonando wallpha-cli $GIT_BRANCH em $TARGET via git..."
    mkdir -p "$(dirname "$TARGET")"
    git clone --branch "$GIT_BRANCH" --depth 1 "$REPO" "$TARGET" 2>&1 | sed 's/^/  /' || {
      echo "falha no git clone de $GIT_BRANCH, tentando master..." >&2
      git clone --depth 1 "$REPO" "$TARGET" 2>&1 | sed 's/^/  /'
    }
  fi
  # propaga flags se suportado
  EXTRA_ARGS=()
  if [ "$WANTS_DEV" -eq 1 ] && grep -q -- "--dev" "$TARGET/install.sh" 2>/dev/null; then EXTRA_ARGS+=("--dev"); fi
  if [ "$WANTS_BIN" -eq 1 ] && grep -q -- "--bin" "$TARGET/install.sh" 2>/dev/null; then EXTRA_ARGS+=("--bin"); fi
  exec "$TARGET/install.sh" "${EXTRA_ARGS[@]}" "${INSTALL_ARGS[@]}"
fi

# modo tarball (padrão, sem git, sem jq) — baixa release
ASSET_VER="$VERSION_NOV"
# auto-detecta bin/dev se já instalado e usuário não passou --bin/--dev explícito
# usa .wallpha-variant (criado pelo install.sh) — independe do yml que o user pode editar
if [ "$WANTS_BIN" -eq 0 ] && [ "$WANTS_DEV" -eq 0 ] && [ -d "$TARGET" ]; then
  if [ -f "$TARGET/.wallpha-variant" ]; then
    case "$(cat "$TARGET/.wallpha-variant" 2>/dev/null | tr -d '[:space:]')" in
      bin) WANTS_BIN=1 ;;
      dev) WANTS_DEV=1 ;;
    esac
  elif [ -f "$TARGET/wallpha.yml" ]; then
    # fallback para instalações antigas sem .wallpha-variant (1.0.2): detecta via yml/assets
    if grep -q 'local: ~/Imagens$' "$TARGET/wallpha.yml" 2>/dev/null; then
      WANTS_BIN=1
    elif [ ! -d "$TARGET/assets/wallpapers" ] && [ ! -d "$TARGET/src/wallpha/assets" ] && grep -q 'local: ~/Imagens' "$TARGET/wallpha.yml" 2>/dev/null; then
      WANTS_BIN=1
    fi
  fi
  # fallback final: sem assets e com conteúdo → bin (full sempre tem default-wallpha.png)
  if [ "$WANTS_BIN" -eq 0 ] && [ "$WANTS_DEV" -eq 0 ] && [ -d "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ] && [ ! -d "$TARGET/assets/wallpapers" ] && [ ! -d "$TARGET/src/wallpha/assets" ] && [ -f "$TARGET/wallpha.yml" ]; then
    WANTS_BIN=1
  fi
fi
# bin usa wallpha-cli-bin, full usa wallpha-cli
if [ "$WANTS_BIN" -eq 1 ]; then
  PKG_BASE="wallpha-cli-bin"
else
  PKG_BASE="wallpha-cli"
fi
TARBALL_URL="https://github.com/EuSouPedroEmanoel/wallpha-cli/releases/download/$TAG/${PKG_BASE}-$ASSET_VER.tar.gz"
ZIP_URL="https://github.com/EuSouPedroEmanoel/wallpha-cli/releases/download/$TAG/${PKG_BASE}-$ASSET_VER.zip"
# fallback para wallpha-cli se bin asset não existir (compat: bin ainda não tem release separada)
TARBALL_FALLBACK="https://github.com/EuSouPedroEmanoel/wallpha-cli/releases/download/$TAG/wallpha-cli-$ASSET_VER.tar.gz"
ZIP_FALLBACK="https://github.com/EuSouPedroEmanoel/wallpha-cli/releases/download/$TAG/wallpha-cli-$ASSET_VER.zip"

echo "==> Baixando $PKG_BASE $TAG via tarball..."
TMPDIR="$(mktemp -d)"
cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

DL_OK=0
DL_TARBALL=""
if have curl; then
  if curl -fsSL "$TARBALL_URL" -o "$TMPDIR/wallpha.tar.gz" 2>/dev/null; then
    DL_OK=1; DL_TARBALL="$TARBALL_URL"
  elif [ "$WANTS_BIN" -eq 1 ] && curl -fsSL "$TARBALL_FALLBACK" -o "$TMPDIR/wallpha.tar.gz" 2>/dev/null; then
    echo "  (bin asset não encontrado, usando wallpha-cli fallback)"
    DL_OK=1; DL_TARBALL="$TARBALL_FALLBACK"
  elif curl -fsSL "$ZIP_URL" -o "$TMPDIR/wallpha.zip" 2>/dev/null; then
    # fallback zip se tar.gz não existir (ex.: conexão)
    if have unzip; then
      echo "  extraindo zip $ASSET_VER..."
      unzip -q "$TMPDIR/wallpha.zip" -d "$TMPDIR"
      DL_OK=2
    fi
  elif [ "$WANTS_BIN" -eq 1 ] && curl -fsSL "$ZIP_FALLBACK" -o "$TMPDIR/wallpha.zip" 2>/dev/null && have unzip; then
    echo "  (bin asset não encontrado, usando wallpha-cli fallback)"
    unzip -q "$TMPDIR/wallpha.zip" -d "$TMPDIR"
    DL_OK=2
  fi
elif have wget; then
  if wget -qO "$TMPDIR/wallpha.tar.gz" "$TARBALL_URL" 2>/dev/null; then
    DL_OK=1; DL_TARBALL="$TARBALL_URL"
  elif [ "$WANTS_BIN" -eq 1 ] && wget -qO "$TMPDIR/wallpha.tar.gz" "$TARBALL_FALLBACK" 2>/dev/null; then
    DL_OK=1; DL_TARBALL="$TARBALL_FALLBACK"
  elif wget -qO "$TMPDIR/wallpha.zip" "$ZIP_URL" 2>/dev/null && have unzip; then
    unzip -q "$TMPDIR/wallpha.zip" -d "$TMPDIR"
    DL_OK=2
  elif [ "$WANTS_BIN" -eq 1 ] && wget -qO "$TMPDIR/wallpha.zip" "$ZIP_FALLBACK" 2>/dev/null && have unzip; then
    unzip -q "$TMPDIR/wallpha.zip" -d "$TMPDIR"
    DL_OK=2
  fi
else
  echo "erro: curl ou wget necessário para modo tarball (ou use --git)" >&2
  exit 1
fi

if [ "$DL_OK" -eq 0 ]; then
  echo "erro: falha ao baixar $TARBALL_URL" >&2
  echo "tente --git ou verifique a versão em https://github.com/EuSouPedroEmanoel/wallpha-cli/releases" >&2
  exit 1
fi

if [ "$DL_OK" -eq 1 ]; then
  echo "  extraindo tar.gz $ASSET_VER..."
  mkdir -p "$TMPDIR/extract"
  tar xzf "$TMPDIR/wallpha.tar.gz" -C "$TMPDIR/extract" --strip-components=1 2>/dev/null || tar xzf "$TMPDIR/wallpha.tar.gz" -C "$TMPDIR/extract" 2>/dev/null
  EXTRACTED="$TMPDIR/extract"
else
  EXTRACTED="$(find "$TMPDIR" -maxdepth 2 -name "wallpha-cli*-*" -type d | head -n1)"
  if [ -z "$EXTRACTED" ]; then
    EXTRACTED="$(find "$TMPDIR" -maxdepth 2 -name "wallpha-cli*" -type d | head -n1)"
  fi
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

EXTRA_ARGS=()
if [ "$WANTS_DEV" -eq 1 ] && grep -q -- "--dev" "$TARGET/install.sh" 2>/dev/null; then EXTRA_ARGS+=("--dev"); fi
if [ "$WANTS_BIN" -eq 1 ] && grep -q -- "--bin" "$TARGET/install.sh" 2>/dev/null; then EXTRA_ARGS+=("--bin"); fi
exec "$TARGET/install.sh" "${EXTRA_ARGS[@]}" "${INSTALL_ARGS[@]}"
