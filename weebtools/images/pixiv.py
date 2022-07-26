import json
import re
import requests

from .imageDownloader import ImageDownloader
from ..utils import (
    askQuestion, sanitize,
)
from ..weebException import WeebException


class Pixiv(ImageDownloader):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

    def download_single(self,piclink):
        ''' Can be worker or called explcitly for one time download '''
        picID = self.checkValid(piclink,'pixiv','single')

        s = requests.Session()
        r = s.get(f'https://www.pixiv.net/ajax/illust/{picID}')

        j = r.json()
        if j['error']:
            raise WeebException(j['message'])

        artist = sanitize(j['body']['userName'])
        pngDir, jpgDir, sourceDir = self.setupArtistDir(artist)

        basePicTitle = f'{picID}_{j["body"]["illustTitle"]}'
        pageCount = j['body']['userIllusts'][picID]['pageCount']

        end = '' if pageCount == 1 else f' ({pageCount} pictures)'
        with self.lock:
            print(f'Downloading {piclink}{end}', flush=True)
        for p in range(pageCount):
            picUrl = re.sub('_p0',f'_p{p}',j['body']['urls']['original'])
            with s.get(picUrl,headers={'referer':piclink},stream=True) as r:
                if r.status_code != 200:
                    raise WeebException(f'Cannot get original image {r.status_code}')

                ext = 'png' if r.headers['Content-Type'] == 'image/png' else 'jpg'
                picTitle = sanitize(f'{basePicTitle}_p{p}.{ext}')
                picDir = pngDir if ext == 'png' else jpgDir
                picture = picDir / picTitle

                if picture.is_file():
                    if pageCount > 1:
                        continue
                    elif askQuestion(f'Picture p{p} already eixsts, continue?')=='n':
                        raise WeebException('User cancelled download')

                with open(picture,'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            if cl := r.headers.get('Content-Length'):
                fs = picture.stat().st_size
                if fs != int(cl):
                    picture.unlink()
                    raise WeebException(f'{picture} File size mismatch {fs} != {cl}')

            isExplicit = any(x['tag'] == 'R-18' for x in j['body']['tags']['tags'])
            with self.lock:
                self.updateInfoFile(sourceDir,{
                    'piclink': piclink,
                    'artistlink': f'https://www.pixiv.net/en/users/{j["body"]["tags"]["authorId"]}',
                    'explicit': isExplicit,
                })
                self.summary[ext].append({
                    'artist': artist,
                    'picture': picture,
                    'explicit': isExplicit,
                })
