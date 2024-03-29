# This is a personal fork of [Komikku](https://www.gitlab.com/valos/Komikku)

This is a fork of Komikku and NOT the official repo. It will almost definitely have issues. The `personal` branch is where I make my changes. Most of the time, both upstream and this branch are **essentially the same** because I try to upstream all the working changes asap and I have a pretty comfortable reading environment here now.

Basically, don't use this.

Major differences right now (in order of stability):

* Chapters are downloaded in the order that you selected them in the Chapters list and not based on chapter list sorting. Seems stable, especially since it simply adds a variable and that's basically it.
* Search within chapter lists, only accessible by beginning to type. There is no search button. The selection behavior during search works as I want and expect it to work, but it might not be ideal for everyone.
* MangaDex BBCode support in synopsis or manga description and possible HTML support in other sites.
* Experimental Tachiyomi backup import functionality. Not sure it'll work for anyone else and even if it does, it's not assured to properly work at least.

The actual README follows. It's mostly the same as the official README.

# <a href="https://valos.gitlab.io/Komikku/"><img height="88" src="data/icons/info.febvre.Komikku.svg" />Komikku</a>

[![pipeline status](https://gitlab.com/fushinari/Komikku/badges/personal/pipeline.svg)](https://gitlab.com/fushinari/Komikku/commits/personal)
[![Please do not theme this app](https://stopthemingmy.app/badge.svg)](https://stopthemingmy.app)

Komikku is a manga reader for [GNOME](https://www.gnome.org). It focuses on providing a clean, intuitive and adaptive interface.

## License

Komikku is licensed under the [GPLv3+](https://www.gnu.org/licenses/gpl-3.0.html).

## Keys features

* Online reading from dozens of servers
* Offline reading of downloaded comics
* Categories to organize your library
* RTL, LTR, Vertical and Webtoon reading modes
* Several types of navigation:
  * Keyboard arrow keys
  * Mouse click
  * Mouse wheel
  * 2-fingers swipe gesture
  * Swipe gesture on touch screens
* Automatic update of comics
* Automatic download of new chapters
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

Komikku is available as a native package in the repositories of the following distributions:

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
* `python` >= 3.8
* `gtk` >= 3.24.1
* `libhandy` >= 1.2.0
* `python-beautifulsoup4`
* `python-brotli`
* `python-cloudscraper`
* `python-dateparser`
* `python-keyring` >= 21.6.0
* `python-lxml`
* `python-magic` or `file-magic`
* `python-natsort`
* `python-pillow`
* `python-pure-protobuf`
* `python-unidecode`

This is the best practice to test Komikku without installing using meson and ninja.

#### First time

```bash
git clone https://gitlab.com/valos/Komikku
make setup
make local
```

#### Later on

```bash
make local
```

#### To Run

```bash
make run
```

To use the development profile, use `make develop` instead of `make local`.

### Option 3: Build and install system-wide directly with Meson

**WARNING**: This approach is discouraged, since it will manually copy all the files in your system. **Uninstalling could be difficult and/or dangerous**.

But if you know what you're doing, here you go:

```bash
git clone https://gitlab.com/valos/Komikku
cd Komikku
make
make install
```

If you've already used Option 2, do:

```bash
make clean
make
make install
```

You may need to run `make install` with `sudo`.

## Code of Conduct

We follow the [GNOME Code of Conduct](/CODE_OF_CONDUCT.md).
All communications in project spaces are expected to follow it.

## Translations

Helping to translate Komikku or add support to a new language is very welcome.

## Disclaimer

The developer of this application does not have any affiliation with the content providers available.
