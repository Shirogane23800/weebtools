import argparse
import re
import sys

from . import utils
from .images.imageDownloader import ImageDownloader
from .images.yande import Yande
from .images.pixiv import Pixiv
from .weebException import WeebException


def main_utils(args):
    if args.getChromeVersion:
        print(utils.getChromeVersion())

    if args.getChromeDriverVersion:
        print(utils.getChromeDriverVersion())

    if args.downloadChromeDriver:
        utils.downloadChromeDriver()

def main_img(args):
    if ImageDownloader.checkValid(args.url,'yande','single'):
        yande = Yande()
        yande.download_single(args.url)
        yande.printSummary('single')
    elif ImageDownloader.checkValid(args.url,'yande','artist'):
        yande = Yande(
            update=args.update,
            update_all=args.update_all,
        )
        yande.download_artist(args.url)
        yande.printSummary('artist')
    else:
        raise WeebException(f'Unsupported url: {args.url}')

def getDescription(downloader):
    descrip = ''
    for sv in downloader.valid.values():
        for k,v in sv.items():
            descrip += f'{k}:\n' + '\n'.join(f' - {regex}' for regex in v) + '\n'
    return descrip

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='python -m weebtools',
        description='A tool collection to get anime web related stuff')
    parser.add_argument('--version',
        action='store_true',
        help='Show package version')
    subparsers = parser.add_subparsers(
        title='subcommands',
        dest='command')

    utilsParser = subparsers.add_parser('utils')
    utilsParser.add_argument('--getChromeVersion',
        action='store_true',
        help='Print google chrome version')
    utilsParser.add_argument('--getChromeDriverVersion',
        action='store_true',
        help='Print google ChromeDriver version')
    utilsParser.add_argument('--downloadChromeDriver',
        action='store_true',
        help='Download latest ChromeDriver')

    parent_subparser = argparse.ArgumentParser(add_help=False)
    parent_subparser.add_argument('url',
        help='Top level url')
    group = parent_subparser.add_mutually_exclusive_group()
    group.add_argument('-u','--update',
        action='store_true',
        help='Downloads until the latest data have been found')
    group.add_argument('-ua','--update_all',
        action='store_true',
        help='Downloads any missing data')

    imageParser = subparsers.add_parser('img',
        formatter_class=argparse.RawTextHelpFormatter,
        parents=[parent_subparser],
        description=getDescription(ImageDownloader))

    args = parser.parse_args()

    if args.version:
        import importlib.metadata
        try:
            print(importlib.metadata.version(__package__))
        except ModuleNotFoundError:
            sys.exit('Dev setup, run in venv to get version: pip install -e .')

    try:
        if args.command == 'utils':
            main_utils(args)
        elif args.command == 'img':
            main_img(args)
    except WeebException as e:
        sys.exit(e)
