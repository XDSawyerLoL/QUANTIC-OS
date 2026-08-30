Name: quantic-services
Version: 1.1.0
Release: 1%{?dist}
Summary: Quantic OS local intelligence and safety services
License: MIT
Source0: %{name}-%{version}.tar.gz
BuildArch: noarch
BuildRequires: systemd-rpm-macros
Requires: python3
Requires: python3-psutil
Requires: python3-numpy
Requires: util-linux
Requires: udisks2
Requires: NetworkManager
Requires: pipewire-utils
Requires: wine
%description
Local-first Quantic services and independent Live USB storage guard.
%prep
%autosetup
%build
%install
install -d %{buildroot}%{_prefix}/lib/quantic/services
cp -a services/*.py services/*.sh %{buildroot}%{_prefix}/lib/quantic/services/
chmod 0755 %{buildroot}%{_prefix}/lib/quantic/services/*.py %{buildroot}%{_prefix}/lib/quantic/services/*.sh
install -Dm644 systemd/quantic-resource.service %{buildroot}%{_unitdir}/quantic-resource.service
install -Dm644 systemd/quantic-usb-safe.service %{buildroot}%{_unitdir}/quantic-usb-safe.service
install -Dm644 systemd/user/quantic-companion.service %{buildroot}%{_userunitdir}/quantic-companion.service
install -Dm644 udev/91-quantic-live-storage.rules %{buildroot}%{_udevrulesdir}/91-quantic-live-storage.rules
install -Dm644 polkit/90-quantic-usb-safe.rules %{buildroot}%{_datadir}/polkit-1/rules.d/90-quantic-usb-safe.rules
%post
%systemd_post quantic-resource.service quantic-usb-safe.service
%preun
%systemd_preun quantic-resource.service quantic-usb-safe.service
%postun
%systemd_postun_with_restart quantic-resource.service quantic-usb-safe.service
%files
%{_prefix}/lib/quantic/services/
%{_unitdir}/quantic-resource.service
%{_unitdir}/quantic-usb-safe.service
%{_userunitdir}/quantic-companion.service
%{_udevrulesdir}/91-quantic-live-storage.rules
%{_datadir}/polkit-1/rules.d/90-quantic-usb-safe.rules
