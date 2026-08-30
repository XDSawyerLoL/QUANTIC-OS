Name: quantic-shell
Version: 1.1.0
Release: 1%{?dist}
Summary: Quantic OS premium Qt/QML home surface
License: MIT
Source0: %{name}-%{version}.tar.gz
BuildRequires: gcc-c++
BuildRequires: cmake
BuildRequires: ninja-build
BuildRequires: qt6-qtbase-devel
BuildRequires: qt6-qtdeclarative-devel
BuildRequires: qt6-qtsvg-devel
Requires: plasma-workspace
Requires: qt6-qtdeclarative
Requires: qt6-qtsvg
Requires: dolphin
Requires: plasma-discover
Requires: konsole
%description
Native Quantic Home dashboard running on KDE Plasma/Wayland.
%prep
%autosetup
%build
cmake -S shell -B build -GNinja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=%{_prefix} -DCMAKE_INSTALL_LIBEXECDIR=%{_libexecdir}
cmake --build build --parallel
%install
DESTDIR=%{buildroot} cmake --install build
install -Dm644 shell/autostart/quantic-home.desktop %{buildroot}%{_sysconfdir}/xdg/autostart/quantic-home.desktop
install -Dm644 shell/autostart/quantic-companion.desktop %{buildroot}%{_sysconfdir}/xdg/autostart/quantic-companion.desktop
%files
%{_libexecdir}/quantic-home
%config(noreplace) %{_sysconfdir}/xdg/autostart/quantic-home.desktop
%config(noreplace) %{_sysconfdir}/xdg/autostart/quantic-companion.desktop
