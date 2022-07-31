# weebtools

A tool mostly for downloading anime related stuff.

## Installation
`pip install weebtools`

## Usage
weebtools uses subcommands to split functionality. Each subcommand has their own arguments and options.

## CLI
---

### Top level options:
 - `--help` - Prints help, also shows subcommands
 - `--version` - Prints package version

Examples:
```
python -m weebtools --help
python -m weebtools --version
```
---
### utils

- Used mostly for miscellaneous helper functions

#### General usage

`python -m weebtools utils [some_option(s)]`

Options:
  - `--help` - Print help
  - `--getChromeVersion` - Prints current google chrome version
  - `--getChromeDriverVersion` - Prints current chrome driver version, looking in `$HOME/bin`
  - `--downloadChromeDriver` - Downloads latest chrome driver for your google chrome version

Examples
```
python -m weebtools utils --help
python -m weebtools utils --getChromeVersion
python -m weebtools utils --getChromeDriverVersion
python -m weebtools utils --downloadChromeDriver
```

---
### img

Sites and url format supported:
- yande.re
  - `https://yande.re/post/show/[PIC_ID]`
  - `https://yande.re/post?tags=[ARTIST_TAG_NAME]`
- pixiv
  - `https://www.pixiv.net/en/artworks/[PIC_ID]`
  - `https://www.pixiv.net/en/users/[ARTIST_ID]` - can take different routes, but they all will get from `/artworks`
- More to come!

#### General usage:
`python -m weebtools img <piclink> [some_option(s)]`

Options:
  - No options given:
    - If link type is single, downloads the image
    - If link type is artist, downloads all images from that artist
  - `-h / --help`
    - Prints help
    - Shows what links are supported as well as link type (single vs artist)
  - `-u / --update`
    - If artist folder exist, gets new updates / images until it finds it finds an existing image. (Lazy update)
    - This is particularly useful if the url supplied has lots of pages and you don't want to wait for all page iterations
  - `-ua / --update_all`
    - If artist folder exist, gets any missing images.

Examples:
```
python -m weebtools img -h                                                 # Prints help
python -m weebtools img https://yande.re/post/show/[PIC_ID]                # Downloads single image
python -m weebtools img https://yande.re/post?tags=[ARTIST_TAG_NAME]       # Downloads all images from this artist
python -m weebtools img https://yande.re/post?tags=[ARTIST_TAG_NAME] -u    # Lazy update on this artist
python -m weebtools img https://yande.re/post?tags=[ARTIST_TAG_NAME] -ua   # Updates with any missing images
```



Images are downloaded to `$HOME/Downloads/images`

File system structure:
```
$HOME/Downloads/images
|
└───artist1
|    |
|    └───png
|    |   |
|    │   └── *.png
|    |
|    └───jpg
|    |   |
|    │   └── *.jpg
|    │
|    └───source
|        |
|        └── info.json
|
└───artist2
|    |
|    └───png
|    |   |
|    │   └── *.png
|    |
|    └───jpg
|    |   |
|    │   └── *.jpg
|    │   
|    └───source
|        |
|        └── info.json
|...
```

---
## As a module

- Full of dinosaurs with laser guns

```python
>>> from weebtools.utils import *
>>> getChromeVersion()
'103.0.5060.114'
>>> getChromeDriverVersion()
'103.0.5060.53'
```
