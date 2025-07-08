
# OWNER: t.me/Nezzixccc
pkgname=OWLFetch
pkgver=1.1
pkgrel=3
pkgdesc="THE BEST FETCH IN THE WORLD OF ALL EXISTING. 100% FASTER THAN FASTFETCH AND NEOFETCH. PROVEN BY SCIENTISTS. (The following project is a joke and was created for fun, do not take it seriously)"
arch=('any')
url="https://github.com/uncertainty403/OWLFetch" 
license=('MIT')
depends=('xorg-xrandr' 'lsb-release' 'pciutils' 'inetutils' 'procps-ng')  
source=("$pkgname".sh)
md5sums=('SKIP')

package() {
  install -Dm755 "$srcdir/$pkgname.sh" "$pkgdir/usr/bin/$pkgname"
}
