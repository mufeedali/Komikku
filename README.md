# *Manga Scan* - a manga reader

*Manga Scan* is a [GNOME](https://www.gnome.org) online / offline manga reader, developed with the aim of being used with the *Librem 5* phone.

## License

MangaScan is licensed under the GPLv3+.

## Features

* Online reading from servers
* Offline reading of downloaded mangas
* Light and dark themes

## Building from source

#### Option 1: with GNOME Builder

Open GNOME Builder, click the "Clone..." button, paste the repository url.

Clone the project and hit the "Play" button to start building Manga Scan.

#### Option 2: with Flatpak Builder
```
# Clone Manga Scan repository
git clone https://gitlab.com/valos/MangaScan.git
cd MangaScan
# Add Flathub repository
flatpak remote-add flathub --if-not-exists https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak remote-add gnome-nightly --if-not-exists https://sdk.gnome.org/gnome-nightly.flatpakrepo
# Install the required GNOME runtimes
flatpak install gnome-nightly org.gnome.Platform//master org.gnome.Sdk//master
# Start building
flatpak-builder --repo=repo com.gitlab.valos.MangaScan flatpak/com.gitlab.valos.MangaScan.json --force-clean
# Create the Flatpak
flatpak build-export repo com.gitlab.valos.MangaScan
flatpak build-bundle repo com.gitlab.valos.MangaScan.flatpak com.gitlab.valos.MangaScan
# Install the Flatpak
flatpak install com.gitlab.valos.MangaScan.flatpak
```

#### Option 3: with Meson
##### Prerequisites:
* python >= 3.6.5
* gtk >= 3.24.1
* libhandy >= 0.0.9
* meson >= 0.46.0
* git

```
git clone https://gitlab.com/valos/MangaScan.git
cd MangaScan
meson . _build --prefix=/usr
ninja -C _build
sudo ninja -C _build install
```

## Translations
Helping to translate Manga Scan or add support to a new language is very welcome.

## Disclaimer
The developer of this application does not have any affiliation with the content providers available.

## Authors
</> with &hearts; by Valéry Febvre
