import json
import re
import requests
import time

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .imageDownloader import ImageDownloader
from ..utils import (
    askQuestion, getSeleniumDriver, getSS, getUserPass, removeDirs, sanitize,
)
from ..weebException import WeebException


class Pixiv(ImageDownloader):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.driver = None

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
        pre = f'{self.picList.index(piclink)+1}. ' if piclink in self.picList else ''
        with self.lock:
            print(f'{pre}Downloading {piclink}{end}', flush=True)
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

    def download_artist(self,artistlink):
        '''
        Can't be bothered with pixiv's login api to get cookies
        It's literally recaptcha black magic and the methods change every year
        Just use selenium for stability >_>
        '''
        artistID = self.checkValid(artistlink,'pixiv','artist')

        # change to ... /artworks
        artistlink = f'https://www.pixiv.net/en/users/{artistID}/artworks'

        s, soup = getSS(artistlink)
        j = json.loads(soup.find('meta',id='meta-preload-data')['content'])
        artist = j['user'][artistID]['name']

        print(f'Artist: {artist}',flush=True)

        username, password = getUserPass('pixiv')
        self.driver = getSeleniumDriver(headless=False) # headless mode won't log in...

        artistDir = self.imgFolder / artist
        if artistDir.is_dir():
            if askQuestion(f'"{artist}" already exists, continue?')=='n':
                raise WeebException('User cancelled download')
            removeDirs(artistDir)

        self.summary['artists'].append(artist)

        self._login(username,password)

        # untested, click "keep my email if popup appears to verify"
        # "remind me later" won't have login cookie"
        loginSoup = BeautifulSoup(self.driver.page_source,'html.parser')
        if ((all_a := loginSoup.find_all('a'))
                and any(x.text.lower() == 'remind me later' for x in all_a)):
            raise WeebException('Press "keep your email" on manual pixiv login')

        print('Fetching page 1...',end='',flush=True)
        self.driver.get(artistlink)

        print('Waiting for images to load...')
        soup = self._getPageSoup()

        self.picList = [ f'https://www.pixiv.net{x["href"]}'
            for x in soup.find_all('a',href=re.compile(r'^/en/artworks/\d+$'))
            if x.find() ] # this removes duplicates

        pageRe = re.compile(rf'/en/users/{artistID}/artworks\?p=(\d+)')
        pageTag = sorted(
            set(x['href'] for x in soup.find_all('a',href=pageRe)),
            key=lambda x: pageRe.match(x).group(1))

        if len(pageTag) > 1:
            for page in pageTag[1:]:
                print(f'Fetching page {pageRe.match(page).group(1)}...',end='',flush=True)
                self.driver.get(f'https://www.pixiv.net{page}')

                print('Waiting for images to load...')
                soup = self._getPageSoup()

                self.picList += [ f'https://www.pixiv.net{x["href"]}'
                    for x in soup.find_all('a',href=re.compile(r'^/en/artworks/\d+$'))
                    if x.find() ] # this removes duplicates

        self.close()

        # non logged in vs logged in photos
        r = requests.get(f'https://www.pixiv.net/ajax/user/{artistID}/profile/all')
        print(f'Pictures without login: {len(r.json()["body"]["illusts"])}')
        print(f'Pictures with login: {len(self.picList)}')

        self._download(self.picList)

    def _login(self,username,password):
        self.driver.get('https://accounts.pixiv.net/login')
        print('Logging in pixiv',flush=True)
        self.driver.find_element('xpath',"//input[@autocomplete='username']").send_keys(username)
        self.driver.find_element('xpath',"//input[@autocomplete='current-password']").send_keys(password)
        self.driver.find_element('xpath',"//button[@type='submit']").click()

        # need time to wait for login page to load for cookie to activate (get all photos)
        # don't really know the exact conditions, 10 secs should be good enough
        time.sleep(5)

        if "Incorrect e-mail address or pixiv ID" in self.driver.page_source:
            raise WeebException('Invalid pixiv username')

        if 'Your password must be between' in self.driver.page_source:
            raise WeebException('Invalid pixiv password')

        if 'Please check that' in self.driver.page_source:
            raise WeebException('Invalid pixiv login credentials')

        time.sleep(5)

    def _getPageSoup(self):
        try:
            WebDriverWait(self.driver,20).until(
                EC.visibility_of_element_located(('xpath','//section')))
            time.sleep(5)
        except TimeoutException:
            raise WeebException(f'Cannot load page {page}')
        return BeautifulSoup(self.driver.page_source,'html.parser')

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
