# Maintainer: Pedro Emanoel <pedroemanoeldasilvadeoliveira@gmail.com>
pkgname=wallp-cli
pkgver=1.0.0
pkgrel=1
pkgdesc="CLI para wallpaper animado/imagem no KDE Plasma (Smart Video Wallpaper Reborn) com modo automático por agenda"
arch=('any')
url="https://github.com/EuSouPedroEmanoel/wallp-cli"
license=('MIT')
depends=('python' 'python-dbus' 'python-yaml' 'qt6-multimedia' 'qt6-multimedia-ffmpeg' 'ffmpeg')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools' 'git')
optdepends=(
  'plasma6-wallpapers-smart-video-wallpaper-reborn: plasmoid Smart Video Wallpaper Reborn (recomendado)'
  'yt-dlp: suporte a wallpapers do YouTube (youtube / youtube-list)'
  'yay: instalação automática do plasmoid via install.sh'
)
source=("git+https://github.com/EuSouPedroEmanoel/wallp-cli.git#tag=v${pkgver}")
sha256sums=('SKIP')
# Para AUR, use `makepkg --printsrcinfo > .SRCINFO` antes de `git push` no AUR.
# Alternativa stable sem git: source=("$pkgname-$pkgver.tar.gz::https://github.com/EuSouPedroEmanoel/wallp-cli/archive/refs/tags/v$pkgver.tar.gz")

build() {
  cd "$pkgname"
  python -m build --wheel --no-isolation
}

package() {
  cd "$pkgname"
  python -m installer --destdir="$pkgdir" dist/*.whl

  # bin wrapper extra (além do entry_point wallp em /usr/bin/wallp)
  install -Dm755 bin/wallp "$pkgdir/usr/share/wallp/bin/wallp"

  # exemplos e documentação
  install -Dm644 wallp.yml.example "$pkgdir/usr/share/doc/$pkgname/wallp.yml.example"
  install -Dm644 wallp.yml "$pkgdir/usr/share/doc/$pkgname/wallp.yml"
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"

  # systemd user service — ExecStart aponta para /usr/bin/wallp (entry_point)
  install -Dm644 systemd/wallp-daemon.service "$pkgdir/usr/lib/systemd/user/wallp-daemon.service"
  # corrige ExecStart para o binário instalado pelo pip (/usr/bin/wallp)
  sed -i 's|ExecStart=.*|ExecStart=/usr/bin/wallp -d|' "$pkgdir/usr/lib/systemd/user/wallp-daemon.service"

  # licença (se houver, senão gera a partir do README)
  if [ -f LICENSE ]; then
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  fi
}
