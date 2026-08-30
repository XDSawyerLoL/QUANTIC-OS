Name: quantic-theme
Version: 1.1.0
Release: 1%{?dist}
Summary: Quantic OS Plasma defaults and visual assets
License: MIT
Source0: %{name}-%{version}.tar.gz
BuildArch: noarch
Requires: plasma-workspace
%description
Quantic visual defaults for Plasma 6.
%prep
%autosetup
%build
%install
install -d %{buildroot}%{_datadir}/plasma/look-and-feel/org.quantic.desktop
cp -a plasma/org.quantic.desktop/* %{buildroot}%{_datadir}/plasma/look-and-feel/org.quantic.desktop/
install -Dm644 assets/quantic-wallpaper.svg %{buildroot}%{_datadir}/backgrounds/quantic/quantic-wallpaper.svg
%files
%{_datadir}/plasma/look-and-feel/org.quantic.desktop/
%{_datadir}/backgrounds/quantic/
