#!/usr/bin/env bash
# wallpha — instalador/verificador.
# Garante que o computador tem tudo para o wallpha funcionar:
# python3 + dbus/yaml, codecs de vídeo, o plasmoid Smart Video Wallpaper Reborn,
# o binário em ~/.local/bin, o config ~/.config/wallpha/wallpha.yml e o daemon systemd.
#
# Uso:  ./install.sh [-y|--yes] [--check] [--dev] [--bin]
#   -y      instala dependências faltando sem perguntar (usa sudo / yay)
#   --check só verifica, não altera nada
#   --dev   modo desenvolvimento: mantém código em ~/dev/wallpha/wallpha-cli (symlink),
#           padrão sem --dev instala em ~/.local/share/wallpha (XDG, sem deixar nada em ~/dev)
#   --bin   pacote mínimo wallpha-cli-bin: sem capa padrão, sem repo dev,
#           wallpaper padrão pego de ~/Imagens (não ~/Imagens/wallpha), sem copiar wallpapers

set -euo pipefail

# ---------------------------------------------------------------- migração wallp → wallpha (v2.0.0 compat, remove em 3.0)
if [ "${WALLPHA_SKIP_MIGRATION:-0}" != 1 ]; then
    # config
    if [ -d "$HOME/.config/wallp" ] && [ ! -d "$HOME/.config/wallpha" ]; then
        cp -a "$HOME/.config/wallp" "$HOME/.config/wallpha" 2>/dev/null || true
        echo "  (migração: ~/.config/wallp → ~/.config/wallpha)"
    fi
    if [ -f "$HOME/.config/wallp/wallp.yml" ] && [ ! -f "$HOME/.config/wallpha/wallpha.yml" ]; then
        mkdir -p "$HOME/.config/wallpha" 2>/dev/null || true
        cp -a "$HOME/.config/wallp/wallp.yml" "$HOME/.config/wallpha/wallpha.yml" 2>/dev/null || true
    fi
    if [ -f "$HOME/.config/wallpha/wallpha.yml" ]; then
        # atualiza path antigo dentro do yml se ainda apontar para ~/Imagens/wallp
        sed -i 's|~/Imagens/wallp|~/Imagens/wallpha|g' "$HOME/.config/wallpha/wallpha.yml" 2>/dev/null || true
    fi
    if [ -f "$HOME/.config/wallpha/wallp.yml" ] && [ ! -f "$HOME/.config/wallpha/wallpha.yml" ]; then
        mv "$HOME/.config/wallpha/wallp.yml" "$HOME/.config/wallpha/wallpha.yml" 2>/dev/null || true
    fi
    # state
    if [ -d "$HOME/.local/state/wallp" ] && [ ! -d "$HOME/.local/state/wallpha" ]; then
        cp -a "$HOME/.local/state/wallp" "$HOME/.local/state/wallpha" 2>/dev/null || true
        echo "  (migração: ~/.local/state/wallp → ~/.local/state/wallpha)"
    fi
    # share
    if [ -d "$HOME/.local/share/wallp" ] && [ ! -d "$HOME/.local/share/wallpha" ]; then
        cp -a "$HOME/.local/share/wallp" "$HOME/.local/share/wallpha" 2>/dev/null || true
        echo "  (migração: ~/.local/share/wallp → ~/.local/share/wallpha)"
    fi
    if [ -d "$HOME/.local/share/wallp-plasma" ] && [ ! -d "$HOME/.local/share/wallpha-plasma" ]; then
        cp -a "$HOME/.local/share/wallp-plasma" "$HOME/.local/share/wallpha-plasma" 2>/dev/null || true
    fi
    # wallpapers dir
    if [ -d "$HOME/Imagens/wallp" ] && [ ! -d "$HOME/Imagens/wallpha" ]; then
        mv "$HOME/Imagens/wallp" "$HOME/Imagens/wallpha" 2>/dev/null || cp -a "$HOME/Imagens/wallp" "$HOME/Imagens/wallpha" 2>/dev/null || true
        echo "  (migração: ~/Imagens/wallp → ~/Imagens/wallpha)"
    elif [ -d "$HOME/Imagens/wallp" ] && [ -d "$HOME/Imagens/wallpha" ]; then
        # copia faltantes sem sobrescrever
        cp -an "$HOME/Imagens/wallp"/* "$HOME/Imagens/wallpha"/ 2>/dev/null || true
    fi
    if [ -f "$HOME/Imagens/wallpha/default-wallp.png" ] && [ ! -f "$HOME/Imagens/wallpha/default-wallpha.png" ]; then
        mv "$HOME/Imagens/wallpha/default-wallp.png" "$HOME/Imagens/wallpha/default-wallpha.png" 2>/dev/null || true
    fi
    # systemd old unit
    if [ -f "$HOME/.config/systemd/user/wallp-daemon.service" ] && [ ! -f "$HOME/.config/systemd/user/wallpha-daemon.service" ]; then
        cp -a "$HOME/.config/systemd/user/wallp-daemon.service" "$HOME/.config/systemd/user/wallpha-daemon.service" 2>/dev/null || true
        systemctl --user disable wallp-daemon.service 2>/dev/null || true
    fi
fi

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

# auto-detect dev: se já está em ~/dev/wallpha/* com .git, assume --dev mesmo sem flag
if [ "$DEV" -eq 0 ] && [[ "$PROJ_ROOT" == "$HOME/dev/wallpha"* ]] && [ -d "$PROJ_ROOT/.git" ]; then
    DEV=1
fi

# destino da instalação: dev (~/dev) ou XDG_DATA_HOME (~/.local/share/wallpha)
XDG_DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
WALLPHA_DATA="$XDG_DATA/wallpha"
if [ "$DEV" -eq 1 ]; then
    INSTALL_ROOT="$PROJ_ROOT"
else
    INSTALL_ROOT="$WALLPHA_DATA"
    # se PROJ_ROOT já é o destino (ex.: já instalado via quick-install tarball em ~/.local/share/wallpha), não copia
    if [ "$PROJ_ROOT" != "$INSTALL_ROOT" ] && [ "$CHECK" != 1 ]; then
        mkdir -p "$INSTALL_ROOT"
        # copia arquivos essenciais para rodar wallpha a partir de ~/.local/share/wallpha
        # wallpha.yml não fica no repo (só wallpha.yml.example), é gerado direto em ~/.config
        for item in bin src assets pyproject.toml wallpha_cli.py wallpha.yml.example; do
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
        echo "bin" > "$INSTALL_ROOT/.wallpha-variant" 2>/dev/null || true
    elif [ "$DEV" -eq 1 ]; then
        echo "dev" > "$INSTALL_ROOT/.wallpha-variant" 2>/dev/null || true
    else
        echo "full" > "$INSTALL_ROOT/.wallpha-variant" 2>/dev/null || true
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

detect_pm() {
    if have pacman; then echo "pacman"
    elif have apt-get; then echo "apt"
    elif have dnf; then echo "dnf"
    elif have zypper; then echo "zypper"
    elif have emerge; then echo "emerge"
    else echo ""
    fi
}
PM="$(detect_pm)"

install_pkg() {
    if [ "$CHECK" = 1 ]; then return 0; fi
    if [ -z "$PM" ]; then no "$* (instale manualmente)"; return 1; fi
    if ! ask; then no "$*"; return 1; fi
    case "$PM" in
        pacman) sudo pacman -S --needed "$@" ;;
        apt) sudo apt-get update -qq 2>/dev/null; sudo apt-get install -y "$@" ;;
        dnf) sudo dnf install -y "$@" ;;
        zypper) sudo zypper install -y "$@" ;;
        emerge) sudo emerge "$@" ;;
        *) no "$* (gerenciador $PM não suportado)"; return 1 ;;
    esac
}

run_pacman() { install_pkg "$@"; }

# ---------------------------------------------------------------- python
step "Python"
if have python3; then ok "python3 ($(python3 --version 2>&1))"; else no "python3"; exit 1; fi

for mod in dbus yaml; do
    if python3 -c "import $mod" 2>/dev/null; then
        ok "python3:$mod"
    else
        case "$PM" in
            apt) pkg="python3-$mod"; [ "$mod" = yaml ] && pkg="python3-yaml" ;;
            dnf|zypper) pkg="python3-$mod"; [ "$mod" = yaml ] && pkg="python3-pyyaml" ;;
            *) pkg="python-$mod"; [ "$mod" = yaml ] && pkg="python-yaml" ;;
        esac
        no "python3:$mod ($pkg)"
        install_pkg "$pkg" || true
    fi
done

# ---------------------------------------------------------------- codecs
step "Codecs de vídeo (qt6-multimedia) — KDE Plasma 6 em qualquer distro"
if [ "$PM" = "pacman" ]; then
    for pkg in qt6-multimedia qt6-multimedia-ffmpeg; do
        if pacman -Q "$pkg" >/dev/null 2>&1; then ok "$pkg"; else no "$pkg"; install_pkg "$pkg" || true; fi
    done
elif [ "$PM" = "apt" ]; then
    for pkg in qml6-module-qtmultimedia qt6-multimedia-dev gstreamer1.0-plugins-bad; do
        if dpkg -l "$pkg" 2>/dev/null | grep -q "^ii"; then ok "$pkg"; else no "$pkg"; install_pkg "$pkg" || true; fi
    done
    # extra-cmake-modules para build do plasmóide (só build, pode remover depois)
    if dpkg -l "extra-cmake-modules" 2>/dev/null | grep -q "^ii"; then ok "extra-cmake-modules"; else no "extra-cmake-modules"; install_pkg "extra-cmake-modules" || true; fi
elif [ "$PM" = "dnf" ]; then
    for pkg in qt6-qtmultimedia qt6-qtmultimedia-devel kf6-plasma; do
        if rpm -q "$pkg" >/dev/null 2>&1; then ok "$pkg"; else no "$pkg"; install_pkg "$pkg" || true; fi
    done
    if rpm -q "extra-cmake-modules" >/dev/null 2>&1; then ok "extra-cmake-modules"; else no "extra-cmake-modules"; install_pkg "extra-cmake-modules" || true; fi
elif [ "$PM" = "zypper" ]; then
    for pkg in qt6-multimedia qt6-multimedia-ffmpeg kf6-plasma6; do
        if rpm -q "$pkg" >/dev/null 2>&1; then ok "$pkg"; else no "$pkg"; install_pkg "$pkg" || true; fi
    done
    if rpm -q "extra-cmake-modules" >/dev/null 2>&1; then ok "extra-cmake-modules"; else no "extra-cmake-modules"; install_pkg "extra-cmake-modules" || true; fi
else
    for pkg in qt6-multimedia qt6-multimedia-ffmpeg; do
        no "$pkg (instale manualmente para $PM)"; install_pkg "$pkg" || true
    done
    no "extra-cmake-modules (apenas build, pode remover depois)"; install_pkg "extra-cmake-modules" || true
fi
# verifica qt6-declarative (QML) — já vem com Plasma 6 na maioria das distros
if [ "$PM" = "pacman" ]; then
    if pacman -Q "qt6-declarative" >/dev/null 2>&1; then ok "qt6-declarative"; else no "qt6-declarative"; install_pkg "qt6-declarative" || true; fi
elif [ "$PM" = "apt" ]; then
    if dpkg -l "qml6-module-qtquick" 2>/dev/null | grep -q "^ii"; then ok "qml6-module-qtquick"; else no "qml6-module-qtquick"; install_pkg "qml6-module-qtquick" || true; fi
elif [ "$PM" = "dnf" ] || [ "$PM" = "zypper" ]; then
    if rpm -q "qt6-qtdeclarative" >/dev/null 2>&1; then ok "qt6-qtdeclarative"; else no "qt6-qtdeclarative"; install_pkg "qt6-qtdeclarative" || true; fi
fi

# ---------------------------------------------------------------- plasmoid
step "Plasmoid wallpha (com.wallpha.wallpaper) unificado"
PLASMOID="com.wallpha.wallpaper"
PLASMOID_LEGACY="luisbocanegra.smart.video.wallpaper.reborn"
# tenta instalar o novo plasmóide a partir de ../plasma-wallpaper-wallpha se existir (dev)
PLASMOID_SRC="$PROJ_ROOT/../wallpha-plasma"
if [ ! -d "$PLASMOID_SRC" ]; then
    PLASMOID_SRC="$HOME/dev/wallpha/wallpha-plasma"
fi
if [ -d "/usr/share/plasma/wallpapers/$PLASMOID" ] || [ -d "$HOME/.local/share/plasma/wallpapers/$PLASMOID" ]; then
    ok "plasmoid $PLASMOID"
elif [ -d "$PLASMOID_SRC/contents" ] && [ -f "$PLASMOID_SRC/metadata.json" ]; then
    no "plasmoid $PLASMOID (instalando local de $PLASMOID_SRC)"
    if [ "$CHECK" = 1 ]; then ok "plasmóide local disponível em $PLASMOID_SRC"; else
        if [ -x "$PLASMOID_SRC/install.sh" ]; then
            bash "$PLASMOID_SRC/install.sh" && ok "plasmoid $PLASMOID instalado (local cmake/cp)"
        elif command -v cmake >/dev/null 2>&1; then
            cmake -B "$PLASMOID_SRC/build" --install-prefix "$HOME/.local" >/dev/null && cmake --install "$PLASMOID_SRC/build" >/dev/null && ok "plasmoid $PLASMOID instalado (cmake)"
        else
            mkdir -p "$HOME/.local/share/plasma/wallpapers/$PLASMOID/contents"
            cp -a "$PLASMOID_SRC/metadata.json" "$HOME/.local/share/plasma/wallpapers/$PLASMOID/" 2>/dev/null && cp -a "$PLASMOID_SRC/contents/"* "$HOME/.local/share/plasma/wallpapers/$PLASMOID/contents/" 2>/dev/null && ok "plasmoid $PLASMOID instalado (cp)"
        fi
    fi
else
    # fallback legado
    if [ -d "/usr/share/plasma/wallpapers/$PLASMOID_LEGACY" ] || [ -d "$HOME/.local/share/plasma/wallpapers/$PLASMOID_LEGACY" ]; then
        ok "plasmoid $PLASMOID_LEGACY (legado, prefira $PLASMOID)"
    else
        no "plasmoid $PLASMOID"
        if have yay; then
            if [ "$CHECK" = 1 ]; then ok "yay disponível (instale com: yay -S plasma6-wallpapers-smart-video-wallpaper-reborn ou instale $PLASMOID de $PLASMOID_SRC)"; else
            if ask; then
                # tenta novo plasmóide via AUR futuro, cai para legado
                if yay -S --needed wallpha-plasma 2>/dev/null || yay -S --needed plasma6-wallpapers-wallpha 2>/dev/null; then
                    ok "plasmoid $PLASMOID instalado via yay"
                else
                    yay -S --needed plasma6-wallpapers-smart-video-wallpaper-reborn && ok "plasmoid $PLASMOID_LEGACY instalado via yay (legado)"
                fi
            else no "plasmoid (não instalado)"; fi; fi
        else
            no "yay (instale o plasmoid manualmente: $PLASMOID_SRC ou AUR plasma6-wallpapers-smart-video-wallpaper-reborn)"
        fi
    fi
    # auto-baixa wallpha-plasma via tarball se ainda não instalado (sem depender de yay/dev)
    if [ ! -d "/usr/share/plasma/wallpapers/$PLASMOID" ] && [ ! -d "$HOME/.local/share/plasma/wallpapers/$PLASMOID" ] && [ ! -d "$PLASMOID_SRC/contents" ]; then
        if [ "$CHECK" = 1 ]; then
            no "wallpha-plasma não instalado (seria baixado via GitHub releases)"
        else
            if have curl || have wget; then
                PLASMA_TAG="v1.0.0"
                PLASMA_VER="1.0.0"
                # tenta latest via GitHub API
                if have curl; then
                    LATEST_TAG=$(curl -fsSL https://api.github.com/repos/EuSouPedroEmanoel/wallpha-plasma/releases/latest 2>/dev/null | grep -o '"tag_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || true)
                    if [ -n "$LATEST_TAG" ]; then PLASMA_TAG="$LATEST_TAG"; PLASMA_VER="${LATEST_TAG#v}"; fi
                elif have wget; then
                    LATEST_TAG=$(wget -qO- https://api.github.com/repos/EuSouPedroEmanoel/wallpha-plasma/releases/latest 2>/dev/null | grep -o '"tag_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || true)
                    if [ -n "$LATEST_TAG" ]; then PLASMA_TAG="$LATEST_TAG"; PLASMA_VER="${LATEST_TAG#v}"; fi
                fi
                TARBALL_URL="https://github.com/EuSouPedroEmanoel/wallpha-plasma/releases/download/$PLASMA_TAG/wallpha-plasma-$PLASMA_VER.tar.gz"
                TMPDIR_PLASMA="$(mktemp -d)"
                PLASMA_DEST="$HOME/.local/share/wallpha-plasma"
                echo "  Baixando wallpha-plasma $PLASMA_TAG via tarball..."
                DL_OK=0
                if have curl; then
                    if curl -fsSL "$TARBALL_URL" -o "$TMPDIR_PLASMA/wallpha-plasma.tar.gz" 2>/dev/null; then DL_OK=1; fi
                elif have wget; then
                    if wget -qO "$TMPDIR_PLASMA/wallpha-plasma.tar.gz" "$TARBALL_URL" 2>/dev/null; then DL_OK=1; fi
                fi
                if [ "$DL_OK" = 1 ]; then
                    mkdir -p "$PLASMA_DEST"
                    # limpa destino antigo (mantém se for git dev, mas aqui é XDG)
                    if [ -d "$PLASMA_DEST/.git" ]; then
                        echo "  (preservando $PLASMA_DEST/.git dev)"
                    else
                        rm -rf "$PLASMA_DEST" 2>/dev/null || true
                        mkdir -p "$PLASMA_DEST"
                    fi
                    if tar xzf "$TMPDIR_PLASMA/wallpha-plasma.tar.gz" -C "$PLASMA_DEST" --strip-components=1 2>/dev/null || tar xzf "$TMPDIR_PLASMA/wallpha-plasma.tar.gz" -C "$PLASMA_DEST" 2>/dev/null; then
                        if [ -x "$PLASMA_DEST/install.sh" ]; then
                            bash "$PLASMA_DEST/install.sh" -y >/dev/null 2>&1 && ok "plasmoid $PLASMOID instalado via tarball $PLASMA_TAG em $PLASMA_DEST" || no "falha ao instalar wallpha-plasma via tarball"
                        else
                            no "wallpha-plasma tarball sem install.sh"
                        fi
                    else
                        no "falha ao extrair wallpha-plasma tarball"
                    fi
                else
                    no "falha ao baixar $TARBALL_URL"
                fi
                rm -rf "$TMPDIR_PLASMA" 2>/dev/null || true
                # atualiza PLASMOID_SRC para daemon usar se instalou
                if [ -d "$HOME/.local/share/plasma/wallpapers/$PLASMOID" ] || [ -d "/usr/share/plasma/wallpapers/$PLASMOID" ]; then
                    PLASMOID_SRC="$HOME/.local/share/plasma/wallpapers/$PLASMOID"
                fi
            else
                no "curl/wget necessário para baixar wallpha-plasma (ou instale via --dev / yay)"
            fi
        fi
    fi
fi

# ---------------------------------------------------------------- plasma
step "Plasmashell"
if pgrep -x plasmashell >/dev/null 2>&1; then ok "plasmashell rodando"; else no "plasmashell (sessão headless? o daemon vai fechar sozinho)"; fi

# ---------------------------------------------------------------- bin
step "Binário (~/.local/bin/wallpha)"
mkdir -p "$HOME/.local/bin"
ln -sf "$PROJ_ROOT/bin/wallpha" "$HOME/.local/bin/wallpha"
# compat wallp → wallpha por 1 release (remove em 3.0)
ln -sf "$HOME/.local/bin/wallpha" "$HOME/.local/bin/wallp" 2>/dev/null || true
if [ -x "$HOME/.local/bin/wallpha" ]; then ok "wallpha -> $HOME/.local/bin/wallpha (compat wallp)"; else no "wallpha em ~/.local/bin"; fi
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ok "~/.local/bin no PATH" ;;
    *) no "~/.local/bin fora do PATH (adicione: export PATH=\$HOME/.local/bin:\$PATH)" ;;
esac

# ---------------------------------------------------------------- config
step "Configuração (~/.config/wallpha/wallpha.yml)"
CFG="$HOME/.config/wallpha/wallpha.yml"
if [ ! -f "$CFG" ]; then
    if [ "$CHECK" = 1 ]; then no "config $CFG"; else
        mkdir -p "$(dirname "$CFG")"
        # só wallpha.yml.example fica no repo; wallpha.yml é gerado direto em ~/.config
        if [ "$BIN" -eq 1 ]; then
            cat > "$CFG" <<'YML'
# wallpha — agenda de wallpapers (gerado: bin minimal)
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
# wallpha — agenda de wallpapers (gerado pelo install.sh)
- nome: padrao
  type: diretório
  local: ~/Imagens/wallpha
  tempo: 30s
  loop: true
  shuffled: true
  default: true
YML
            ok "config criado: $CFG (full: ~/Imagens/wallpha)"
        fi
    fi
else
    ok "config já existe: $CFG"
fi
# pasta padrão do yml — cria se não existir
if [ "$CHECK" != 1 ]; then
    if [ "$BIN" -eq 1 ]; then
        # bin: wallpaper padrão é ~/Imagens direto, sem subpasta wallpha, sem capa
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
        # full: ~/Imagens/wallpha com capa padrão
        if have xdg-user-dir; then
            _pics="$(xdg-user-dir PICTURES 2>/dev/null || echo "")"
            if [ -z "$_pics" ] || [ "$_pics" = "$HOME" ]; then
                if [ -d "$HOME/Imagens" ]; then _pics="$HOME/Imagens"; else _pics="$HOME/Pictures"; fi
            fi
        else
            if [ -d "$HOME/Imagens" ]; then _pics="$HOME/Imagens"; else _pics="$HOME/Pictures"; fi
        fi
        mkdir -p "$_pics/wallpha" 2>/dev/null || mkdir -p "$HOME/Imagens/wallpha" 2>/dev/null || true
        if [ -d "$_pics/wallpha" ]; then ok "pasta padrão: $_pics/wallpha"; else ok "pasta padrão: ~/Imagens/wallpha"; fi
        # wallpapers padrão — copia se pasta estiver vazia (primeiro -a)
        if [ -d "$_pics/wallpha" ] && [ -z "$(ls -A "$_pics/wallpha" 2>/dev/null)" ]; then
            SRC_DIR=""
            if [ -d "$PROJ_ROOT/assets/wallpapers" ]; then SRC_DIR="$PROJ_ROOT/assets/wallpapers"
            elif [ -d "$PROJ_ROOT/src/wallpha/assets" ]; then SRC_DIR="$PROJ_ROOT/src/wallpha/assets"
            fi
            if [ -n "$SRC_DIR" ] && [ -n "$(ls -A "$SRC_DIR" 2>/dev/null)" ]; then
                cp "$SRC_DIR"/* "$_pics/wallpha/" 2>/dev/null && ok "wallpapers padrão copiados para $_pics/wallpha/ ($(ls -1 "$_pics/wallpha" 2>/dev/null | wc -l) imagens)"
            fi
        fi
    fi
fi

# ---------------------------------------------------------------- daemon (migrado para wallpha-plasma)
step "Daemon (systemd --user) — canônico em wallpha-plasma"
UNIT="wallpha-daemon.service"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
# daemon agora é de wallpha-plasma; este install delega se wallpha-plasma existir
PLASMA_ROOT="$HOME/dev/wallpha/wallpha-plasma"
if [ -d "$PLASMA_ROOT/bin" ] && [ -f "$PLASMA_ROOT/bin/wallpha-plasma-daemon" ]; then
    DAEMON_EXEC="$HOME/.local/bin/wallpha-plasma-daemon"
    DAEMON_DESC="wallpha-plasma — daemon de wallpaper (agenda + com.wallpha.wallpaper)"
    # garante bin linkado
    if [ "$CHECK" != 1 ]; then ln -sf "$PLASMA_ROOT/bin/wallpha-plasma-daemon" "$HOME/.local/bin/wallpha-plasma-daemon" 2>/dev/null || true; fi
elif [ -x "$HOME/.local/bin/wallpha-plasma-daemon" ]; then
    DAEMON_EXEC="$HOME/.local/bin/wallpha-plasma-daemon"
    DAEMON_DESC="wallpha-plasma — daemon de wallpaper (agenda + com.wallpha.wallpaper)"
elif [ -x "/usr/local/bin/wallpha-plasma-daemon" ] || [ -x "/usr/bin/wallpha-plasma-daemon" ]; then
    if [ -x "/usr/local/bin/wallpha-plasma-daemon" ]; then DAEMON_EXEC="/usr/local/bin/wallpha-plasma-daemon"; else DAEMON_EXEC="/usr/bin/wallpha-plasma-daemon"; fi
    DAEMON_DESC="wallpha-plasma — daemon de wallpaper (agenda + com.wallpha.wallpaper)"
else
    DAEMON_EXEC="/usr/bin/python3 $PROJ_ROOT/bin/wallpha -d"
    DAEMON_DESC="wallpha - modo automático de wallpaper (legado, prefira wallpha-plasma)"
fi
if [ "$CHECK" != 1 ]; then
    cat > "$UNIT_DIR/$UNIT" <<EOF
[Unit]
Description=$DAEMON_DESC
After=plasma-plasmashell.service
PartOf=plasma-plasmashell.service

[Service]
Type=simple
ExecStart=$DAEMON_EXEC
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
fi
if systemctl --user is-enabled "$UNIT" >/dev/null 2>&1; then ok "daemon habilitado ($DAEMON_EXEC)"; else no "daemon não habilitado"; fi
if [ "$CHECK" != 1 ]; then
    systemctl --user daemon-reload >/dev/null 2>&1 || true
    systemctl --user enable "$UNIT" >/dev/null 2>&1 || true
    ok "daemon habilitado (inicia com o computador) via ${DAEMON_EXEC}"
    if [[ "$DAEMON_EXEC" == *"wallpha-plasma"* ]] && [ -x "$PLASMA_ROOT/install.sh" ]; then
        # delega instalação completa do daemon ao wallpha-plasma (plasmóide já instalado acima)
        bash "$PLASMA_ROOT/install.sh" -y >/dev/null 2>&1 || true
    fi
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
echo "  wallpha -c [caminho|nome]   troca o wallpaper"
echo "  wallpha -n                  próximo wallpaper do yml"
echo "  wallpha -r [dir] -t tempo   modo aleatório (slideshow embaralhado)"
echo "                              -i = só imagens | -v = só vídeos"
echo "                              -m tempo máx (padrão 1h) | -q N | -l true (loop)"
echo "                              -rep = vídeos repetem a reprodução"
echo "                              -int = vídeo toca inteiro; com -t, se terminar antes fica no último frame"
echo "                              -s on|off = som do vídeo (padrão mudo)"
echo "  wallpha -a                  ativa o modo automático"
echo "  wallpha -x                  desativa o modo automático/aleatório"
exit 0
