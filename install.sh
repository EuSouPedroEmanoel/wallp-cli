#!/usr/bin/env bash
# wallp — instalador/verificador.
# Garante que o computador tem tudo para o wallp funcionar:
# python3 + dbus/yaml, codecs de vídeo, o plasmoid Smart Video Wallpaper Reborn,
# o binário em ~/.local/bin, o config ~/.config/wallp/wallp.yml e o daemon systemd.
#
# Uso:  ./install.sh [-y|--yes] [--check] [--dev] [--bin]
#   -y      instala dependências faltando sem perguntar (usa sudo / yay)
#   --check só verifica, não altera nada
#   --dev   modo desenvolvimento: mantém código em ~/dev/wallp/wallp-cli (symlink),
#           padrão sem --dev instala em ~/.local/share/wallp (XDG, sem deixar nada em ~/dev)
#   --bin   pacote mínimo wallp-cli-bin: sem capa padrão, sem repo dev,
#           wallpaper padrão pego de ~/Imagens (não ~/Imagens/wallp), sem copiar wallpapers

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "$0")" && pwd)"
YES=0
CHECK=0
DEV=0
BIN=0
for a in "$@"; do
    case "$a" in
        -y|--yes) YES=1 ;;
        --check) CHECK=1 ;;
        --dev) DEV=1 ;;
        --bin) BIN=1 ;;
        *) echo "uso: $0 [-y] [--check] [--dev] [--bin]"; exit 1 ;;
    esac
done

# auto-detect dev: se já está em ~/dev/wallp/* com .git, assume --dev mesmo sem flag
if [ "$DEV" -eq 0 ] && [[ "$PROJ_ROOT" == "$HOME/dev/wallp"* ]] && [ -d "$PROJ_ROOT/.git" ]; then
    DEV=1
fi

# destino da instalação: dev (~/dev) ou XDG_DATA_HOME (~/.local/share/wallp)
XDG_DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
WALLP_DATA="$XDG_DATA/wallp"
if [ "$DEV" -eq 1 ]; then
    INSTALL_ROOT="$PROJ_ROOT"
else
    INSTALL_ROOT="$WALLP_DATA"
    # se PROJ_ROOT já é o destino (ex.: já instalado via quick-install tarball em ~/.local/share/wallp), não copia
    if [ "$PROJ_ROOT" != "$INSTALL_ROOT" ] && [ "$CHECK" != 1 ]; then
        mkdir -p "$INSTALL_ROOT"
        # copia arquivos essenciais para rodar wallp a partir de ~/.local/share/wallp
        # wallp.yml não fica no repo (só wallp.yml.example), é gerado direto em ~/.config
        for item in bin src assets pyproject.toml wallp_cli.py wallp.yml.example; do
            if [ -e "$PROJ_ROOT/$item" ]; then
                cp -a "$PROJ_ROOT/$item" "$INSTALL_ROOT/" 2>/dev/null || true
            fi
        done
        # garante .git não vai junto no modo não-dev
        rm -rf "$INSTALL_ROOT/.git" 2>/dev/null || true
        PROJ_ROOT="$INSTALL_ROOT"
    fi
fi

# marca variante instalada para quick-install auto-detectar (independe do yml que o user pode editar)
if [ "$CHECK" != 1 ]; then
    mkdir -p "$INSTALL_ROOT" 2>/dev/null || true
    if [ "$BIN" -eq 1 ]; then
        echo "bin" > "$INSTALL_ROOT/.wallp-variant" 2>/dev/null || true
    elif [ "$DEV" -eq 1 ]; then
        echo "dev" > "$INSTALL_ROOT/.wallp-variant" 2>/dev/null || true
    else
        echo "full" > "$INSTALL_ROOT/.wallp-variant" 2>/dev/null || true
    fi
fi

OK=0; FAIL=0
step() { printf '\n==> %s\n' "$1"; }
ok() { printf '  OK   %s\n' "$1"; OK=$((OK+1)); }
no() { printf '  FALTA %s\n' "$1"; FAIL=$((FAIL+1)); }
have() { command -v "$1" >/dev/null 2>&1; }

ask() {
    if [ "$YES" = 1 ]; then return 0; fi
    read -r -p "  Instalar agora? [s/N] " r
    [ "${r,,}" = s ] || [ "${r,,}" = sim ]
}

run_pacman() {
    if [ "$CHECK" = 1 ]; then return 0; fi
    if ask; then sudo pacman -S --needed "$@"; else no "$*"; fi
}

# ---------------------------------------------------------------- python
step "Python"
if have python3; then ok "python3 ($(python3 --version 2>&1))"; else no "python3"; exit 1; fi

for mod in dbus yaml; do
    if python3 -c "import $mod" 2>/dev/null; then
        ok "python3:$mod"
    else
        pkg="python-$mod"
        [ "$mod" = yaml ] && pkg="python-yaml"
        no "python3:$mod ($pkg)"
        run_pacman "$pkg"
    fi
done

# ---------------------------------------------------------------- codecs
step "Codecs de vídeo (qt6-multimedia)"
for pkg in qt6-multimedia qt6-multimedia-ffmpeg; do
    if pacman -Q "$pkg" >/dev/null 2>&1; then ok "$pkg"; else no "$pkg"; run_pacman "$pkg"; fi
done

# ---------------------------------------------------------------- plasmoid
step "Plasmoid Smart Video Wallpaper Reborn"
PLASMOID="luisbocanegra.smart.video.wallpaper.reborn"
if [ -d "/usr/share/plasma/wallpapers/$PLASMOID" ] || [ -d "$HOME/.local/share/plasma/wallpapers/$PLASMOID" ]; then
    ok "plasmoid $PLASMOID"
else
    no "plasmoid $PLASMOID"
    if have yay; then
        if [ "$CHECK" = 1 ]; then ok "yay disponível (instale com: yay -S plasma6-wallpapers-smart-video-wallpaper-reborn)"; else
        if ask; then
            yay -S --needed plasma6-wallpapers-smart-video-wallpaper-reborn
            ok "plasmoid instalado via yay"
        else no "plasmoid (não instalado)"; fi; fi
    else
        no "yay (instale o plasmoid manualmente: AUR plasma6-wallpapers-smart-video-wallpaper-reborn)"
    fi
fi

# ---------------------------------------------------------------- plasma
step "Plasmashell"
if pgrep -x plasmashell >/dev/null 2>&1; then ok "plasmashell rodando"; else no "plasmashell (sessão headless? o daemon vai fechar sozinho)"; fi

# ---------------------------------------------------------------- bin
step "Binário (~/.local/bin/wallp)"
mkdir -p "$HOME/.local/bin"
ln -sf "$PROJ_ROOT/bin/wallp" "$HOME/.local/bin/wallp"
if [ -x "$HOME/.local/bin/wallp" ]; then ok "wallp -> $HOME/.local/bin/wallp"; else no "wallp em ~/.local/bin"; fi
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ok "~/.local/bin no PATH" ;;
    *) no "~/.local/bin fora do PATH (adicione: export PATH=\$HOME/.local/bin:\$PATH)" ;;
esac

# ---------------------------------------------------------------- config
step "Configuração (~/.config/wallp/wallp.yml)"
CFG="$HOME/.config/wallp/wallp.yml"
if [ ! -f "$CFG" ]; then
    if [ "$CHECK" = 1 ]; then no "config $CFG"; else
        mkdir -p "$(dirname "$CFG")"
        # só wallp.yml.example fica no repo; wallp.yml é gerado direto em ~/.config
        if [ "$BIN" -eq 1 ]; then
            cat > "$CFG" <<'YML'
# wallp — agenda de wallpapers (gerado: bin minimal)
- nome: padrao
  type: diretório
  local: ~/Imagens
  tempo: 30s
  loop: true
  shuffled: true
  default: true
YML
            ok "config criado: $CFG (bin: ~/Imagens)"
        else
            cat > "$CFG" <<'YML'
# wallp — agenda de wallpapers (gerado pelo install.sh)
- nome: padrao
  type: diretório
  local: ~/Imagens/wallp
  tempo: 30s
  loop: true
  shuffled: true
  default: true
YML
            ok "config criado: $CFG (full: ~/Imagens/wallp)"
        fi
    fi
else
    ok "config já existe: $CFG"
fi
# pasta padrão do yml — cria se não existir
if [ "$CHECK" != 1 ]; then
    if [ "$BIN" -eq 1 ]; then
        # bin: wallpaper padrão é ~/Imagens direto, sem subpasta wallp, sem capa
        if have xdg-user-dir; then
            _pics="$(xdg-user-dir PICTURES 2>/dev/null || echo "")"
            if [ -z "$_pics" ] || [ "$_pics" = "$HOME" ]; then
                if [ -d "$HOME/Imagens" ]; then _pics="$HOME/Imagens"; else _pics="$HOME/Pictures"; fi
            fi
        else
            if [ -d "$HOME/Imagens" ]; then _pics="$HOME/Imagens"; else _pics="$HOME/Pictures"; fi
        fi
        mkdir -p "$_pics" 2>/dev/null || true
        if [ -d "$_pics" ]; then ok "pasta padrão (bin): $_pics"; else ok "pasta padrão (bin): ~/Imagens"; fi
        # bin não copia capa padrão — usa o que já está em ~/Imagens
    else
        # full: ~/Imagens/wallp com capa padrão
        if have xdg-user-dir; then
            _pics="$(xdg-user-dir PICTURES 2>/dev/null || echo "")"
            if [ -z "$_pics" ] || [ "$_pics" = "$HOME" ]; then
                if [ -d "$HOME/Imagens" ]; then _pics="$HOME/Imagens"; else _pics="$HOME/Pictures"; fi
            fi
        else
            if [ -d "$HOME/Imagens" ]; then _pics="$HOME/Imagens"; else _pics="$HOME/Pictures"; fi
        fi
        mkdir -p "$_pics/wallp" 2>/dev/null || mkdir -p "$HOME/Imagens/wallp" 2>/dev/null || true
        if [ -d "$_pics/wallp" ]; then ok "pasta padrão: $_pics/wallp"; else ok "pasta padrão: ~/Imagens/wallp"; fi
        # wallpapers padrão — copia se pasta estiver vazia (primeiro -a)
        if [ -d "$_pics/wallp" ] && [ -z "$(ls -A "$_pics/wallp" 2>/dev/null)" ]; then
            SRC_DIR=""
            if [ -d "$PROJ_ROOT/assets/wallpapers" ]; then SRC_DIR="$PROJ_ROOT/assets/wallpapers"
            elif [ -d "$PROJ_ROOT/src/wallp/assets" ]; then SRC_DIR="$PROJ_ROOT/src/wallp/assets"
            fi
            if [ -n "$SRC_DIR" ] && [ -n "$(ls -A "$SRC_DIR" 2>/dev/null)" ]; then
                cp "$SRC_DIR"/* "$_pics/wallp/" 2>/dev/null && ok "wallpapers padrão copiados para $_pics/wallp/ ($(ls -1 "$_pics/wallp" 2>/dev/null | wc -l) imagens)"
            fi
        fi
    fi
fi

# ---------------------------------------------------------------- daemon
step "Daemon (systemd --user)"
UNIT="wallp-daemon.service"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
if [ "$CHECK" != 1 ]; then
    cat > "$UNIT_DIR/$UNIT" <<EOF
[Unit]
Description=wallp - modo automático de wallpaper
After=plasma-plasmashell.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 $PROJ_ROOT/bin/wallp -d
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
fi
if systemctl --user is-enabled "$UNIT" >/dev/null 2>&1; then ok "daemon habilitado"; else no "daemon não habilitado"; fi
if [ "$CHECK" != 1 ]; then
    systemctl --user daemon-reload >/dev/null 2>&1 || true
    systemctl --user enable "$UNIT" >/dev/null 2>&1 || true
    ok "daemon habilitado (inicia com o computador)"
fi

# ---------------------------------------------------------------- venv (opcional)
if [ "$CHECK" != 1 ] && [ ! -d "$PROJ_ROOT/.venv" ]; then
    # bin não precisa de venv dev
    if [ "$BIN" -eq 0 ]; then
        echo "==> Ambiente de testes (.venv) — opcional"
        python3 -m venv "$PROJ_ROOT/.venv" 2>/dev/null && "$PROJ_ROOT/.venv/bin/pip" install -q pytest pyyaml || no "venv"
    fi
fi

# ---------------------------------------------------------------- resumo
echo
echo "=================================================="
if [ "$FAIL" -gt 0 ]; then
    echo "  $OK ok, $FAIL faltando — revise os itens acima."
    echo "  Rode de novo com ./install.sh -y para instalar tudo."
else
    echo "  Tudo certo ($OK itens)."
fi
echo "=================================================="
echo
echo "Comandos:"
echo "  wallp -c [caminho|nome]   troca o wallpaper"
echo "  wallp -n                  próximo wallpaper do yml"
echo "  wallp -r [dir] -t tempo   modo aleatório (slideshow embaralhado)"
echo "                              -i = só imagens | -v = só vídeos"
echo "                              -m tempo máx (padrão 1h) | -q N | -l true (loop)"
echo "                              -rep = vídeos repetem a reprodução"
echo "                              -int = vídeo toca inteiro; com -t, se terminar antes fica no último frame"
echo "                              -s on|off = som do vídeo (padrão mudo)"
echo "  wallp -a                  ativa o modo automático"
echo "  wallp -x                  desativa o modo automático/aleatório"
exit 0
