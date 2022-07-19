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
                r'^https://yande.re/post/show/\d+$',
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

        j = {}
        if infoFile.is_file():
            j = getJsonData(infoFile)
            j['artistLink'].append(infoData['artistLink'])
            if infoData['explicit']:
                j['explicit'].append(infoData['piclink'])
            j['piclinks'].append(infoData['piclink'])

        writeJsonData({
            'lastUpdate': datetime.datetime.now().strftime('%m-%d-%Y %I:%M:%S %p'),
            'artistLink': sorted(set(j.get('artistLink',[infoData['artistLink']]))),
            'explicit'  : sorted(set(j.get('explicit',[infoData['piclink']] if infoData['explicit'] else [])),reverse=True),
            'piclinks'  : sorted(set(j.get('piclinks',[infoData['piclink']])),reverse=True),
        },infoFile)

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
