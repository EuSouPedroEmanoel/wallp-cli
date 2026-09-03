#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(sed -n 's/^version = "\([^"]*\)"/\1/p' "$ROOT_DIR/pyproject.toml" | head -1)"
OUT_DIR="${1:-$ROOT_DIR/dist}"

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Versão inválida em pyproject.toml: $VERSION" >&2
    exit 1
fi
if [[ -n "${GITHUB_REF_NAME:-}" && "$GITHUB_REF_NAME" != "v$VERSION" ]]; then
    echo "A tag $GITHUB_REF_NAME não corresponde à versão v$VERSION" >&2
    exit 1
fi

STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGE_DIR"' EXIT
mkdir -p "$OUT_DIR"

FULL_NAME="wallpha-cli-$VERSION"
BIN_NAME="wallpha-cli-bin-$VERSION"
mkdir -p "$STAGE_DIR/$FULL_NAME" "$STAGE_DIR/$BIN_NAME"

for item in LICENSE README.md bin install.sh quick-install.sh pyproject.toml src systemd wallpha.yml.example wallpha_cli.py; do
    cp -a "$ROOT_DIR/$item" "$STAGE_DIR/$FULL_NAME/"
    cp -a "$ROOT_DIR/$item" "$STAGE_DIR/$BIN_NAME/"
done
cp -a "$ROOT_DIR/assets" "$STAGE_DIR/$FULL_NAME/"
rm -rf "$STAGE_DIR/$BIN_NAME/assets" "$STAGE_DIR/$BIN_NAME/src/wallpha/assets"
find "$STAGE_DIR" -type d \( -name __pycache__ -o -name .pytest_cache -o -name .venv \) -prune -exec rm -rf {} +

tar -C "$STAGE_DIR" -czf "$OUT_DIR/$FULL_NAME.tar.gz" "$FULL_NAME"
tar -C "$STAGE_DIR" -czf "$OUT_DIR/$BIN_NAME.tar.gz" "$BIN_NAME"
(cd "$STAGE_DIR" && zip -qr "$OUT_DIR/$FULL_NAME.zip" "$FULL_NAME")
(cd "$STAGE_DIR" && zip -qr "$OUT_DIR/$BIN_NAME.zip" "$BIN_NAME")

for artifact in "$OUT_DIR"/wallpha-cli*"$VERSION".{tar.gz,zip}; do
    test -s "$artifact"
done
printf 'Artefatos gerados em %s\n' "$OUT_DIR"
