<p align="center">
    <img width="350" src="https://i.imgur.com/rmZ4myV.png" alt="Ososedki-dl logo">
</p>

<p align="center">
    <a href="https://github.com/YisusChrist/ososedki_dl/issues">
        <img src="https://img.shields.io/github/issues/YisusChrist/ososedki_dl?color=171b20&label=Issues%20%20&logo=gnubash&labelColor=e05f65&logoColor=ffffff">&nbsp;&nbsp;&nbsp;
    </a>
    <a href="https://github.com/YisusChrist/ososedki_dl/forks">
        <img src="https://img.shields.io/github/forks/YisusChrist/ososedki_dl?color=171b20&label=Forks%20%20&logo=git&labelColor=f1cf8a&logoColor=ffffff">&nbsp;&nbsp;&nbsp;
    </a>
    <a href="https://github.com/YisusChrist/ososedki_dl/stargazers">
        <img src="https://img.shields.io/github/stars/YisusChrist/ososedki_dl?color=171b20&label=Stargazers&logo=octicon-star&labelColor=70a5eb">&nbsp;&nbsp;&nbsp;
    </a>
    <a href="https://github.com/YisusChrist/ososedki_dl/actions">
        <img alt="Tests Passing" src="https://github.com/YisusChrist/ososedki_dl/actions/workflows/github-code-scanning/codeql/badge.svg">&nbsp;&nbsp;&nbsp;
    </a>
    <a href="https://github.com/YisusChrist/ososedki_dl/pulls">
        <img alt="GitHub pull requests" src="https://img.shields.io/github/issues-pr/YisusChrist/ososedki_dl?color=0088ff">&nbsp;&nbsp;&nbsp;
    </a>
    <a href="https://deepwiki.com/YisusChrist/ososedki_dl">
        <img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki">&nbsp;&nbsp;&nbsp;
    </a>
    <a href="https://opensource.org/license/GPL-3.0/">
        <img alt="License" src="https://img.shields.io/github/license/YisusChrist/ososedki_dl?color=0088ff">
    </a>
</p>

<br>

<p align="center">
    <a href="https://github.com/YisusChrist/ososedki_dl/issues/new?assignees=YisusChrist&labels=bug&projects=&template=bug_report.yml">Report Bug</a>
    ·
    <a href="https://github.com/YisusChrist/ososedki_dl/issues/new?assignees=YisusChrist&labels=feature&projects=&template=feature_request.yml">Request Feature</a>
    ·
    <a href="https://github.com/YisusChrist/ososedki_dl/issues/new?assignees=YisusChrist&labels=question&projects=&template=question.yml">Ask Question</a>
    ·
    <a href="https://github.com/YisusChrist/ososedki_dl/security/policy#reporting-a-vulnerability">Report security bug</a>
</p>

<br>

![Alt](https://repobeats.axiom.co/api/embed/d776dfb3239e733c3333eb2cf4f8924bd6478660.svg "Repobeats analytics image")

<br>

`ososedki_dl` is a Python app that allows you to download all the images from online albums. The program is designed to be simple and easy to use, with a command-line interface that allows you to download images from the website with a single command. Check the [Supported sites](#supported-sites) section to see the list of supported websites.

## Changes in this fork

This is a fork of [YisusChrist/ososedki_dl](https://github.com/YisusChrist/ososedki_dl). All credit for the original project goes to its author; this section documents what has changed here. The PyPI package still ships the upstream version, so see [Installation](#installation) for how to get this fork instead.

- **Fix:** `ososedki` downloads silently produced empty folders, because the image links on the site are now relative (e.g. `/images/a/1280/.../10.webp`) instead of absolute. Hrefs are now resolved against the site URL before matching, and an album page that yields zero media is now reported and retried as an error instead of silently completing with an empty folder.
- **Fix:** model URLs such as `https://ososedki.com/model/Chuchu+Nagomitei` were rejected with `Unknown URL format`, because `model_url` wasn't configured for `ososedki.com`. URL matching is now path-based, so `http`/`https`, `www`/no-`www`, and a missing trailing slash no longer matter, and `+`/`%20` in names no longer affects matching or folder names.
- **Change:** downloads are now organised as `<download_dir>/<subject>/<set>/` instead of a single flat `<subject>/` folder, falling back to `<subject>/<album id>` when no set name (e.g. cosplay character) is found on the album page, so different sets never mix together. For example, downloading https://ososedki.com/photos/-10000001_10015936:

  ```text
  # Before
  downloads/
  └── Le Josette/
      ├── 1.webp
      ├── 2.webp
      └── ... (32 files)

  # After
  downloads/
  └── Le Josette/
      └── Zhezhi/
          ├── 1.jpg
          ├── 2.jpg
          └── ... (32 files)
  ```

- **Change:** images are converted from WebP to JPG by default (quality 92, optimized, transparency flattened onto a white background, EXIF/ICC metadata preserved when present). Animated WebP files are left as-is, since a JPG can only keep the first frame. The original `.webp` is removed once conversion succeeds. Use `--no-convert` to keep the original WebP files instead — see [WebP to JPG conversion](#webp-to-jpg-conversion) below.
- **New dependency:** [Pillow](https://pypi.org/project/pillow), used for the WebP → JPG conversion above.

<details>
<summary>Table of Contents</summary>

- [Changes in this fork](#changes-in-this-fork)
- [Requirements](#requirements)
- [Installation](#installation)
  - [From PyPI](#from-pypi)
  - [Manual installation](#manual-installation)
  - [Uninstall](#uninstall)
- [Usage](#usage)
  - [Example of execution](#example-of-execution)
  - [Progress bars](#progress-bars)
  - [WebP to JPG conversion](#webp-to-jpg-conversion)
  - [Supported sites](#supported-sites)
- [Contributors](#contributors)
  - [How do I contribute to ososedki\_dl?](#how-do-i-contribute-to-ososedki_dl)
- [License](#license)
- [Credits](#credits)

</details>

## Requirements

Here's a breakdown of the packages needed and their versions:

- [poetry](https://pypi.org/project/poetry) >= 1.7.1 (_only for manual installation_)
- [aiofiles](https://pypi.org/project/aiofiles) >= 24.1.0
- [aiohttp](https://pypi.org/project/aiohttp) >= 3.9.5
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4) >= 4.12.2
- [fake-useragent](https://pypi.org/project/fake-useragent) >= 1.5.1
- [pillow](https://pypi.org/project/pillow) >= 12.3.0 (_this fork, for WebP → JPG conversion_)
- [platformdirs](https://pypi.org/project/platformdirs) >= 4.2.2
- [requests](https://pypi.org/project/requests) >= 2.31.0
- [requests-pprint](https://pypi.org/project/requests-pprint) >= 1.0.1
- [rich](https://pypi.org/project/rich) >= 13.5.3
- [tldextract](https://pypi.org/project/tldextract) >= 5.1.2
- [validators](https://pypi.org/project/validators) >= 0.22.0

> [!NOTE]
> The software has been developed and tested using Python `3.12.1`. The minimum required version to run the software is Python 3.9. Although the software may work with previous versions, it is not guaranteed.

## Installation

### From PyPI

> [!NOTE]
> `pip install ososedki_dl` (and `pipx install ososedki_dl` below) installs the original upstream version from PyPI, which does **not** include this fork's fixes and changes (see [Changes in this fork](#changes-in-this-fork)). To get this fork instead, use [Manual installation](#manual-installation) below, or install straight from GitHub:
>
> ```bash
> pip install git+https://github.com/urbanslayer/ososedki_dl
> ```
>
> or, with pipx:
>
> ```bash
> pipx install git+https://github.com/urbanslayer/ososedki_dl
> ```

`ososedki_dl` can be installed easily as a PyPI package. Just run the following command:

```bash
pip3 install ososedki_dl
```

> [!IMPORTANT]
> For best practices and to avoid potential conflicts with your global Python environment, it is strongly recommended to install this program within a virtual environment. Avoid using the --user option for global installations. We highly recommend using [pipx](https://pypi.org/project/pipx) for a safe and isolated installation experience. Therefore, the appropriate command to install `ososedki_dl` would be:
>
> ```bash
> pipx install ososedki_dl
> ```

The program can now be ran from a terminal with the `ososedki_dl` command.

### Manual installation

If you prefer to install the program manually, follow these steps:

> [!WARNING]
> This will install the version from the latest commit, not the latest release.

1. Download the latest version of [ososedki_dl](https://github.com/urbanslayer/ososedki_dl) (this fork) from this repository:

   ```bash
   git clone https://github.com/urbanslayer/ososedki_dl
   cd ososedki_dl
   ```

2. Install the package:

   ```bash
   poetry install --only main
   ```

3. Run the program:

   ```bash
   poetry run ososedki_dl
   ```

### Uninstall

If you installed it from PyPI, you can use the following command:

```bash
pipx uninstall ososedki_dl
```

## Usage

> [!TIP]
> For more information about the usage of the program, run `ososedki_dl --help` or `ososedki_dl -h`.

![Usage](demo.gif)

The program can be run from the terminal with the `ososedki_dl` command. It will ask you to introduce the URL of the album you want to download. The program will automatically detect the domain, scrape the media (images and videos) and download them to the path specified by the user.

### Example of execution

https://github.com/user-attachments/assets/1b82d20f-1680-4cda-9021-ebd0f87a72ed

### Progress bars

Since 2025-08-18, the program includes progress bars for downloading processes. This feature provides a visual indication of the progress of the operations, making it easier to track the status of the downloads. There are two types of progress bars:

- **Albums**: This bar shows the progress of the whole downloading process, indicating how many items have been downloaded from the album. In case you are downloading a profile, it will display as many bars as albums in the profile, each showing the progress of the respective album. Example:

  https://github.com/user-attachments/assets/691e10c8-4256-4ce1-be88-7684b3798765

- **Videos**: This bar shows the progress of a single video being downloaded. It indicates how much of the video has been downloaded so far.

  https://github.com/user-attachments/assets/8bdc1de9-32eb-4cc2-96ae-061e1df76e1c

### WebP to JPG conversion

By default, every downloaded `.webp` image is converted to `.jpg` (quality 92, optimized, transparency flattened onto a white background, animated WebP left untouched, and the original `.webp` removed once conversion succeeds). Use `--no-convert` to keep the original WebP files instead:

```bash
ososedki_dl --no-convert
```

To be explicit about keeping the default behavior (for example, to override a `convert_webp = false` set in your config file for a single run), pass `--convert`:

```bash
ososedki_dl --convert
```

This can also be set persistently via `convert_webp` under `[Download]` in the config file (inspect it with `ososedki_dl --print-config`) — the `--convert`/`--no-convert` flag always takes precedence over that setting.

> [!NOTE]
> JPGs produced this way are typically larger on disk than the WebP originals, since WebP's compression is generally more efficient than JPEG's at a comparable visual quality.

### Supported sites

| Domain              | URL                           | Scrapping          | Downloading        |
| ------------------- | ----------------------------- | ------------------ | ------------------ |
| `baobua`            | https://baobua.net            | :heavy_check_mark: | :heavy_check_mark: |
| `bunkr-albums`      | https://bunkr-albums.io       | :heavy_check_mark: | :x:\*              |
| `balbums`           | https://balbums.st            | :heavy_check_mark: | :x:\*              |
| `cosplayasian`      | https://cosplayasian.com      | :heavy_check_mark: | :heavy_check_mark: |
| `cosplayboobs`      | https://cosplayboobs.com      | :heavy_check_mark: | :heavy_check_mark: |
| `cosplaykittys`     | https://cosplaykittys.com     | :heavy_check_mark: | :heavy_check_mark: |
| `cosplayleaks`      | https://cosplayleaks.com      | :heavy_check_mark: | :heavy_check_mark: |
| `cosplayrule34`     | https://cosplayrule34.com     | :heavy_check_mark: | :heavy_check_mark: |
| `cosplaysosedki`    | https://cosplaysosedki.com    | :heavy_check_mark: | :heavy_check_mark: |
| `cosplaythots`      | https://cosplaythots.com      | :heavy_check_mark: | :heavy_check_mark: |
| `cosxuxi`           | https://cosxuxi.club          | :heavy_check_mark: | :heavy_check_mark: |
| `depvailon`         | https://www.depvailon.com     | :heavy_check_mark: | :heavy_check_mark: |
| `eromexxx`          | https://eromexxx.com          | :heavy_check_mark: | :heavy_check_mark: |
| `fapello_is`        | https://fapello.is            | :heavy_check_mark: | :heavy_check_mark: |
| `hentaibitches`     | https://hentaibitches.com     | :heavy_check_mark: | :heavy_check_mark: |
| `hentailib`         | https://hentailib.net         | :heavy_check_mark: | :heavy_check_mark: |
| `husvjjal_blogspot` | https://husvjjal.blogspot.com | :heavy_check_mark: | :heavy_check_mark: |
| `kaizty`            | https://www.kaizty.com        | :heavy_check_mark: | :heavy_check_mark: |
| `lootiu`            | https://lootiu.com            | :heavy_check_mark: | :heavy_check_mark: |
| `nungvl`            | https://nungvl.net            | :heavy_check_mark: | :heavy_check_mark: |
| `ocosplay`          | https://ocosplay.com          | :heavy_check_mark: | :heavy_check_mark: |
| `ososedki`          | https://ososedki.com          | :heavy_check_mark: | :heavy_check_mark: |
| `recume`            | https://recu.me               | :heavy_check_mark: | :heavy_check_mark: |
| `sorrymother`       | https://sorrymother.top       | :heavy_check_mark: | :heavy_check_mark: |
| `thismore`          | https://thismore.fun          | :heavy_check_mark: | :heavy_check_mark: |
| `vipthots`          | https://vipthots.com          | :heavy_check_mark: | :heavy_check_mark: |
| `waifubitches`      | https://waifubitches.com      | :heavy_check_mark: | :heavy_check_mark: |
| `wildskirts`        | https://wildskirts.com        | :heavy_check_mark: | :heavy_check_mark: |

**\*** _The program will only scrape the media and display the URLs. You can easily pass all the URLs to the great [CyberDropDownloader](https://github.com/Jules-WinnfieldX/CyberDropDownloader) and download all of them with one command_:

```sh
cyberdrop_dl <URL1> <URL2> <URL3> ...
```

## Contributors

<a href="https://github.com/YisusChrist/ososedki_dl/graphs/contributors"><img src="https://contrib.rocks/image?repo=YisusChrist/ososedki_dl" /></a>

### How do I contribute to ososedki_dl?

Before you participate in our delightful community, please read the [code of conduct](https://github.com/YisusChrist/.github/blob/main/CODE_OF_CONDUCT.md).

I'm far from being an expert and suspect there are many ways to improve – if you have ideas on how to make the configuration easier to maintain (and faster), don't hesitate to fork and send pull requests!

We also need people to test out pull requests. So take a look through [the open issues](https://github.com/YisusChrist/ososedki_dl/issues) and help where you can.

See [Contributing Guidelines](https://github.com/YisusChrist/.github/blob/main/CONTRIBUTING.md) for more details.

## License

`ososedki_dl` is released under the [GPL-3.0 License](https://opensource.org/license/GPL-3.0).

## Credits

![preview](https://opengraph.githubassets.com/963eaba4b5ff0640d87891ec7989d89d70dba767722bdf84d19aa46bda3a933b/Jules-WinnfieldX/CyberDropDownloader)

This program is heavily inspired by [Jules-WinnfieldX](https://github.com/Jules-WinnfieldX)'s [CyberDropDownloader](https://github.com/Jules-WinnfieldX/CyberDropDownloader). Sadly, the project is no longer maintained; hence, the creation of this project to try to bring support for more websites and improve the codebase.
