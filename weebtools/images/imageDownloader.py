import concurrent.futures
import datetime
import itertools
import re
import threading

from pathlib import Path

from ..utils import (
    getJsonData, writeJsonData, makeDirs,
)
from ..weebException import WeebException


class ImageDownloader:

    valid = {
        'yande': {
            'single': [
                r'^https://yande.re/post/show/(\d+)$',
            ],
            'artist': [
                r'^https://yande.re/post\?tags=(.*)+?$',
            ],
        },
        'pixiv': {
            'single': [
                r'^https://www.pixiv.net/en/artworks/(\d+)$',
            ],
            'artist': [
                r'^https://www.pixiv.net/en/users/(\d+)/?$',
                r'^https://www.pixiv.net/en/users/(\d+)/artworks.*$',
                r'^https://www.pixiv.net/en/users/(\d+)/illustrations.*$',
                r'^https://www.pixiv.net/en/users/(\d+)/bookmarksi.*$',
            ],
        },
    }

    failFile = Path.home() / '.weebtools' / 'fail.txt'

    @classmethod
    def checkValid(cls,link,site,linkType):
        try:
            r = next(x for x in cls.valid[site][linkType] if re.match(x,link))
        except StopIteration:
            if cls is ImageDownloader:
                return False
            raise WeebException(f'Invalid link {link} {site} {linkType}')
        return re.match(r,link).group(1)


    def __init__(self,**kwargs):
        ''' Parent downloader class, common things go here '''
        self.imgFolder = Path.home() / 'Downloads' / 'images'
        self.imgFolder.mkdir(parents=True,exist_ok=True)

        self.lock = threading.Lock()

        self.picList = []
        self.summary = {
            'artists': [],
            'success': [],
            'fail': [],
            'png': [],
            'jpg': [],
        }

        self.update = kwargs.get('update')
        self.update_all = kwargs.get('update_all')

        if self.update and self.update_all:
            raise WeebException('--update / --update_all are mutually exclusive')

    def updateInfoFile(self,sourceDir,infoData):
        infoFile = sourceDir / 'info.json'

        now = datetime.datetime.now().strftime('%m-%d-%Y %I:%M:%S %p')
        if infoFile.is_file():
            j = getJsonData(infoFile)
            j['lastUpdate'] = now

            j['artistlink'].append(infoData['artistlink'])
            j['artistlink'] = sorted(set(j['artistlink']))

        else:
            j = {
                'lastUpdate': now,
                'artistlink': [infoData['artistlink']],
                'explicit': { site: [] for site in self.valid },
                'piclinks': { site: [] for site in self.valid },
            }

        for site,v in self.valid.items():
            for r in v['single']:
                if (com := re.compile(r)).match(infoData['piclink']):
                    customSort = lambda x: int(com.match(x).group(1))

                    if infoData['explicit']:
                        j['explicit'][site].append(infoData['piclink'])
                        j['explicit'][site] = sorted(set(j['explicit'][site]),key=customSort,reverse=True)

                    j['piclinks'][site].append(infoData['piclink'])
                    j['piclinks'][site] = sorted(set(j['piclinks'][site]),key=customSort,reverse=True)

                    break

        writeJsonData(j,infoFile)

    def printSummary(self,state='single'):

        picTypes = [
            'png',
            'jpg',
        ]
        picData = [ p for x in picTypes for p in self.summary[x] ]
        if not picData:
            print('NO SUMMARY')
            return

        print('='*50)

        if state == 'single':
            pd = picData[0]
            print(f'Artist: {pd["artist"]}')
            print(f'Title: {pd["picture"].name}')
            if pd['explicit']:
                print('Explicit: True')
            if len(picData) > 1:
                print(f'Total: {len(picData)} pictures')
            print(f'Stored in: {pd["picture"].parent}')

        elif state == 'artist':
            print(f'Artist: {self.summary["artists"][0]}')
            print(f'Total pics: {len(picData)}')
            print('\n'.join(f'{x.upper()}: {len(self.summary[x])}' for x in picTypes))
            if explicitCount := sum(1 for x in picData if x['explicit']):
                print(f'Explicit: {explicitCount}')
            if self.summary['fail']:
                print(f'Success: {len(self.summary["success"])}')
                print(f'Fail: {len(self.summary["fail"])}')
                print(f'View {self.failFile} for failures')

        print('='*50)

    def _download(self,piclinks):
        ''' Multithread download '''
        print(f'Downloading {len(piclinks)} pics')
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(self.download_single,pl):pl for pl in piclinks}

        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
                self.summary['success'].append(futures[f])
            except Exception as e:
                self.summary['fail'].append(f'{futures[f]} {e}')

        if self.summary['fail']:
            self.failFile.parent.mkdir(exist_ok=True)
            self.failFile.write_text('\n'.join(self.summary['fail']))

    def getLazyUpdates(self,listAll,listCurrent,init=False):
        updateList = list(itertools.takewhile(
                lambda x: x not in listCurrent,listAll))

        if init and not updateList:
            raise WeebException('Everything up to date')

        return updateList

    def getAllUpdates(self,listAll,listCurrent):
        return [ x for x in listAll if x not in listCurrent ]

    def setupArtistDir(self,artist):
        artistDir   = self.imgFolder / artist
        pngDir      = artistDir / 'png'
        jpgDir      = artistDir / 'jpg'
        sourceDir   = artistDir / 'source'
        with self.lock:
            makeDirs(artistDir,pngDir,jpgDir,sourceDir)
        return pngDir, jpgDir, sourceDir
