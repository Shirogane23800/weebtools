import threading
import re
from ..weebException import WeebException
from ..utils import getJsonData, writeJsonData
import datetime
from pathlib import Path


class ImageDownloader:

    valid = {
        'yande': {
            'single': [
                r'^https://yande.re/post/show/(\d+)$',
            ],
        },
    }


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

        self.summary = {
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
        print('='*50)

        if state == 'single':
            summaryData = [l for v in self.summary.values() for l in v]
            if not summaryData:
                print('NONE')
                return
            sd = summaryData[0]
            print(f'Artist: {sd["artist"]}')
            print(f'Title: {sd["picture"].name}')
            if sd['explicit']:
                print('Explicit: True')
            print(f'Stored in: {sd["picture"].parent}')

        print('='*50)
