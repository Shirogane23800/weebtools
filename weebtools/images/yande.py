import requests
from bs4 import BeautifulSoup
import sys
import re
import json
from pathlib import Path
from ..utils import (
    getSS, makeDirs, askQuestion, getHash, sanitize
)
from .imageDownloader import ImageDownloader
from ..weebException import WeebException


class Yande(ImageDownloader):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

    def download_single(self,piclink):
        ''' Can be worker or called explcitly for one time download '''
        self.checkValid(piclink,'yande','single')

        print(f'Downloading {piclink}',flush=True)

        s, soup = getSS(piclink)

        artist = 'NO_ARTIST'
        tagTypes = [
            'artist',
            'copyright',
            'circle',
        ]
        for tt in tagTypes:
            tag = soup.find('li',class_=f'tag-type-{tt}')
            if tag:
                t = tag.find('a',href=re.compile('/post\?tags=.*'))
                artist = t.text
                break
        artist = sanitize(artist)

        artistDir   = self.imgFolder / artist
        pngDir      = artistDir / 'png'
        jpgDir      = artistDir / 'jpg'
        sourceDir   = artistDir / 'source'

        with self.lock:
            makeDirs(artistDir,pngDir,jpgDir,sourceDir)

        respInfo = json.loads(re.match('.*?({.*}).*',
            soup.find('div',id='post-view').find('script').text).group(1))['posts'][0]

        # Priority
        # 1. PNG (png)
        # 2. Download larger version (highres)
        # 3. View larger version (highres-show)
        realTag = soup.find('a',id='png') \
               or soup.find('a',id='highres') \
               or soup.find('a',id='highres-show')
        if not realTag:
            raise WeebException('Cannot get file url Tags')

        # Download larger version gives sample url
        # for example https://yande.re/post/show/697638
        if respInfo['file_url'] != realTag['href']:
            # File url differ
            print(f'NOTE: FILE URL DIFFER {piclink}')

        # stream download, uses file_url in the js obj
        with s.get(respInfo['file_url'],stream=True) as r:
            if r.status_code != 200:
                raise WeebException(f'Image file_url error: {r.status_code}')
            if respInfo['file_size'] != int(r.headers['Content-Length']):
                raise WeebException('File size server mismatch ?')

            # extension
            ext = '.png' if r.headers['Content-Type'] == 'image/png' else '.jpg'
            if ext[1:] != respInfo['file_ext']:
                raise WeebException('Wrong file extension')

            # picture title
            sortedTags = sorted(
                x.find('a',href=re.compile('/post\?tags=.*')).text.replace(' ','_')
                for x in soup.find_all('li',class_=re.compile('tag-type.*')))
            if respInfo['tags'] != ' '.join(sortedTags):
                raise WeebException('Wrong tags in file name')
            picTitle = re.sub(r'[\\/:*?"<>|]','_',
                ' '.join(['yande.re',str(respInfo['id'])] + sortedTags) + ext)

            # picture directory
            picDir = pngDir if ext == '.png' else jpgDir

            # picture
            picture = picDir / picTitle

            # windows only allow max 255(260?) chars for file path
            if sys.platform == 'win32':
                while len(str(picture)) >= 255:
                    sortedTags = sortedTags[:-1]
                    picTitle = re.sub(r'[\\/:*?"<>|]','_',
                    ' '.join(['yande.re',artid,] + sortedTags) + ext)
                    picture = picDir / picTitle

            if picture.is_file() and askQuestion('Photo already exists, continue?')=='n':
                raise WeebException('User cancelled download')

            with open(picture,'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        fileSize = picture.stat().st_size
        respSize = respInfo['file_size']
        if fileSize != respSize:
            picture.unlink()
            raise WeebException(f'{picture} File size mismatch {fileSize} != {respSize}')

        if getHash('md5',picture) != respInfo['md5']:
            picture.unlink()
            raise WeebException('md5 checksum failure')

        isExplicit = any(re.match('Rating: Explicit',li.text) for li in soup.find_all('li'))
        with self.lock:
            self.updateInfoFile(sourceDir,{
                'piclink': piclink,
                'artistLink': f'https://yande.re{t["href"]}' if artist != 'NO_ARTIST' else None,
                'explicit': isExplicit,
            })
            self.summary['png' if ext == '.png' else 'jpg'].append({
                'artist': artist,
                'picture': picture,
                'explicit': isExplicit,
            })
