import threading
import re
from ..weebException import WeebException
from ..utils import getJsonData, writeJsonData
import datetime
from pathlib import Path
import concurrent.futures


class ImageDownloader:

    valid = {
        'yande': {
            'single': [
                r'^https://yande.re/post/show/(\d+)$',
            ],
            'artist': [
                r'^https://yande.re/post\?tags=.*$',
            ],
        },
    }

    failFile = Path.home() / '.weebtools' / 'fail.txt'

    @classmethod
    def checkValid(cls,link,site,linkType):
        cond = any(re.match(x,link) for x in cls.valid[site][linkType])
        if cls is ImageDownloader:
            return cond
        if not cond:
            raise WeebException(f'Invalid link {link} {site} {linkType}')


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

    def updateInfoFile(self,sourceDir,infoData):
        infoFile = sourceDir / 'info.json'

        now = datetime.datetime.now().strftime('%m-%d-%Y %I:%M:%S %p')
        if infoFile.is_file():
            j = getJsonData(infoFile)
            j['lastUpdate'] = now

            j['artistlink'].append(infoData['artistlink'])
            j['artistlink'] = sorted(set(j['artistlink']))

            for k,v in self.valid.items():
                for r in v['single']:
                    if (com := re.compile(r)).match(infoData['piclink']):
                        customSort = lambda x: int(com.match(x).group(1))

                        if infoData['explicit']:
                            j['explicit'][k].append(infoData['piclink'])
                            j['explicit'][k] = sorted(set(j['explicit'][k]),key=customSort,reverse=True)

                        j['piclinks'][k].append(infoData['piclink'])
                        j['piclinks'][k] = sorted(set(j['piclinks'][k]),key=customSort,reverse=True)

                        break
        else:
            j = {
                'lastUpdate': now,
                'artistlink': [infoData['artistlink']],
                'explicit': { k: [infoData['piclink']] if infoData['explicit'] else [] for k in self.valid },
                'piclinks': { k: [infoData['piclink']] for k in self.valid },
            }

        writeJsonData(j,infoFile)

    def printSummary(self,state='single'):

        picTypes = [
            'png',
            'jpg',
        ]
        picData = [ p for x in picTypes for p in self.summary[x] ]
        if not picData:
            print('NONE')
            return

        print('='*50)

        if state == 'single':
            pd = picData[0]
            print(f'Artist: {pd["artist"]}')
            print(f'Title: {pd["picture"].name}')
            if pd['explicit']:
                print('Explicit: True')
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
