# <img height="88" src="data/icons/info.febvre.Komikku.svg" /> Komikku

[![pipeline status](https://gitlab.com/valos/Komikku/badges/master/pipeline.svg)](https://gitlab.com/valos/Komikku/commits/master)
[![Please do not theme this app](https://stopthemingmy.app/badge.svg)](https://stopthemingmy.app)

A manga, comics and BDs reader for [GNOME](https://www.gnome.org). The aims of Komikku is to be adaptive (able to scale from desktop workstations to mobile phones).

## License

Komikku is licensed under the [GPLv3+](https://www.gnu.org/licenses/gpl-3.0.html).

## Keys features

* Online reading from servers
* Offline reading of downloaded mangas/comics/BDs
* RTL, LTR, Vertical and Webtoon reading modes
* Four types of navigation:
  * Keyboard arrow keys
  * Mouse click
  * Mouse wheel
  * 2-fingers swipe gesture
* Light and dark themes

## Screenshots

<img src="screenshots/main-window.png" width="290">
<img src="screenshots/add-servers.png" width="290">
<img src="screenshots/preferences.png" width="290">
<img src="screenshots/card-info.png" width="290">
<img src="screenshots/card-chapters.png" width="290">
<img src="screenshots/reader.png" width="290">

## Installation

### Flatpak

<a href='https://flathub.org/apps/details/info.febvre.Komikku'><img width='240' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a>

### Native package

Komikku is available as native package in the repositories of the following distributions:

[![Packaging status](https://repology.org/badge/vertical-allrepos/komikku.svg)](https://repology.org/project/komikku/versions)

### Flatpak of development version

Setup [Flatpak](https://www.flatpak.org/setup/) for your Linux distro. Download the Komikku flatpak from the last passed [Gitlab pipeline](https://gitlab.com/valos/Komikku/pipelines). Then install the flatpak.

```bash
flatpak install info.febvre.Komikku.flatpak
```

## Building from source

### Option 1: Test or building a Flatpak with GNOME Builder

Open GNOME Builder, click the **Clone...** button, paste the repository url.

Clone the project and hit the **Play** button to start building Komikku or test Flatpaks with **Export Bundle** button.

### Option 2: Testing with Meson

Dependencies:

* `git`
* `ninja`
* `meson` >= 0.50.0
* `python` >= 3.6
* `gtk` >= 3.24.1
* `libhandy` >= 1.0.0
* `python-beautifulsoup4`
* `python-dateparser`
* `python-keyring` >= 21.6.0
* `python-lxml`
* `python-magic` or `file-magic`
* `python-pillow`
* `python-pure-protobuf`
* `python-unidecode`
* `python-brotli`
* `python-requests`

This is the best practice to test Komikku without installing using meson and ninja.

#### First time

```bash
git clone https://gitlab.com/valos/Komikku
cd Komikku
mkdir _build
cd _build
meson ..
meson configure -Dprefix=$(pwd)/testdir
ninja install # This will actually install in _build/testdir
ninja run
```

#### Later on

```bash
cd Komikku/_build
ninja install # This will actually install in _build/testdir
ninja run
```

### Option 3: Build and install system-wide directly with Meson

**WARNING**: This approach is discouraged, since it will manually copy all the files in your system. **Uninstalling could be difficult and/or dangerous**.

But if you know what you're doing, here you go:

```bash
git clone https://gitlab.com/valos/Komikku
cd Komikku
mkdir _build
cd _build
meson ..
ninja install
```

## Translations

Helping to translate Komikku or add support to a new language is very welcome.

## Disclaimer

The developer of this application does not have any affiliation with the content providers available.
