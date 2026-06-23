Name:           clack-gui
Version:        2.0.0
Release:        1%{?dist}
Summary:        Extremely realistic human typing simulator (GTK4 GUI)

License:        MIT
URL:            https://github.com/ThisWasAryan/clack
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip
BuildRequires:  python3-wheel
BuildRequires:  python3-build
Requires:       python3-gobject
Requires:       gtk4

%description
Clack is a typing simulator that utilizes probabilistic models to simulate how 
a real human types, complete with realistic rhythms and layout-aware distances.

%prep
%autosetup -n clack-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
install -Dpm0644 org.thiswasaryan.clack.desktop %{buildroot}%{_datadir}/applications/org.thiswasaryan.clack.desktop
install -Dpm0644 gui/assets/clack.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/org.thiswasaryan.clack.png

%files
%{_bindir}/clack-gui
%{python3_sitelib}/gui/
%{python3_sitelib}/clack_gui-*.dist-info/
%{_datadir}/applications/org.thiswasaryan.clack.desktop
%{_datadir}/icons/hicolor/256x256/apps/org.thiswasaryan.clack.png
