# weebtools

A tool mostly for downloading anime related stuff.

### Installation
`pip install weebtools`


## Usage
weebtools uses subcommands to split functionality. Each subcommand has their own arguments and options.

## CLI

## utils

- Used mostly for miscellaneous helper functions
- Be sure to add `$HOME/bin` to your environment `$PATH` veriable

Print help

`python -m weebtools utils --help`

Prints current google chrome version

`python -m weebtools utils --getChromeVersion`

Prints current chrome driver version, looking in `$HOME/bin`

`python -m weebtools utils --getChromeDriverVersion`

Downloads latest chrome driver for your google chrome version

`python -m weebtools utils --downloadChromeDriver`

## img

- Manage and download images to `$HOME/Downloads/images`

Print help

`python -m weebtools img --help`

#### Downloading images

`python -m weebtools img <piclink> [some_option(s)]`

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

Sites and url format supported:
- yande.re
  - https://yande.re/post/show/[...]
- More to come!

## As a module
```python
>>> from weebtools.utils import *
>>> getChromeVersion()
'103.0.5060.114'
>>> getChromeDriverVersion()
'103.0.5060.53'
```
