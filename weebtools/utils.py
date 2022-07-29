import argparse
from pathlib import Path
import sys
import subprocess as sp
import re
import os
import requests
from bs4 import BeautifulSoup
import hashlib
import zipfile
import crc32c
import base64
import struct
import binascii
import json
from .weebException import WeebException
import shutil
import time


_APP_DIR = Path.home() / '.weebtools'
_APP_DIR.mkdir(exist_ok=True)


def getHash(func,x):
    '''
    func        - hash function - md5 / sha1
    x           - thing to hash
    '''
    hashes = {
        'md5':      hashlib.md5(),
        'sha1':     hashlib.sha1(),
        'sha256':   hashlib.sha256(),
    }
    assert func in hashes, f'func must be one of {hashes.keys()}'

    h = hashes[func]
    empty = h.hexdigest()

    if isinstance(x,(str,Path)):
        fp = Path(x)
        if fp.is_file():
            with open(fp,'rb') as f:
                for chunk in iter(lambda: f.read(8192),b''):
                    h.update(chunk)

    if h.hexdigest() == empty:
        h.update(bytes(x))

    return h.hexdigest()

def getChromeVersion():
    '''
    returns MAJOR.MINOR.BUILD.PATCH
    returns None if chrome not installed / other error
    '''
    if sys.platform != 'win32':
        try:
            p = sp.run(['google-chrome','--version'],stdout=sp.PIPE).stdout.decode('utf-8')
            return p.strip().split()[-1]
        except:
            return None

    from win32com.client import Dispatch
    from winreg import OpenKey, HKEY_LOCAL_MACHINE, QueryValueEx
    chromeRegistryPath = os.path.join(
        'SOFTWARE',
        'Microsoft',
        'Windows',
        'CurrentVersion',
        'App Paths',
        'chrome.exe')
    try:
        with OpenKey(HKEY_LOCAL_MACHINE,chromeRegistryPath) as regKey:
            return Dispatch("Scripting.FileSystemObject").GetFileVersion(QueryValueEx(regKey,'')[0])
    except FileNotFoundError:
        print('Chrome not installed?')
    except Exception as e:
        print(e)

def getChromeDriverVersion():
    '''
    returns MAJOR.MINOR.BUILD.PATCH
    returns None if chrome driver not found in _APP_DIR
    '''
    chromeDriver = _APP_DIR / 'chromedriver.exe'

    if not chromeDriver.is_file():
        return None

    p = sp.run([chromeDriver,'--version'],stdout=sp.PIPE).stdout.decode('utf-8')
    return p.split()[1]

def downloadChromeDriver():
    '''
    Downloads chrome driver to _APP_DIR
    Validates download with response checksum headers
    '''
    currentChromeVersion = getChromeVersion()
    if not currentChromeVersion:
        print('Please install Google Chrome to download ChromeDriver')
        return

    majorVersion = currentChromeVersion.split('.')[0]
    base = 'https://chromedriver.storage.googleapis.com'
    com = re.compile(f'^{base}/index.html\?path=({majorVersion}.*)/$')
    print(f'Looking for major version {majorVersion}')
    _, soup = getSS("https://chromedriver.chromium.org/downloads")
    try:
        newVer = com.match(soup.find('a',href=com)['href']).group(1)
    except TypeError:
        print(f'No new ChromeDriver for {majorVersion}')
        return
    print(f'Newest ChromeDriver {newVer}')

    oldChromeDriverVersion = getChromeDriverVersion()
    if oldChromeDriverVersion == newVer:
        print('ChromeDriver up to date')
        return

    print(f'Downloading ChromeDriver',flush=True)

    zipFile = _APP_DIR / f'chromedriver_win32_{newVer}.zip'
    with requests.get(f'{base}/{newVer}/chromedriver_win32.zip',stream=True) as r:
        if not r.status_code == 200:
            print(f'Error getting new ChromeDriver: {r.status_code}')
            return

        with open(zipFile,'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    print('Validating download',flush=True)
    fileSize = zipFile.stat().st_size
    if str(fileSize) != r.headers['x-goog-stored-content-length']:
        zipFile.unlink()
        print(f'Fail file size verification {fileSize} (filesize) != '
            + r.headers['x-goog-stored-content-length'] + ' (headers)')
        return

    hashes = dict(x.split('=',1) for x in r.headers['x-goog-hash'].split(', '))

    # https://github.com/ICRAR/crc32c/issues/14
    zipBytes = zipFile.read_bytes()
    if hashes['crc32c'] != base64.b64encode(struct.pack('>I',crc32c.crc32c(zipBytes))).decode('utf-8'):
        zipFile.unlink()
        print('crc32c checksumn failure')
        return

    md5 = getHash('md5',zipBytes)
    if hashes['md5'] != base64.b64encode(binascii.unhexlify(md5)).decode('utf-8'):
        zipFile.unlink()
        print('md5 checksum failure')
        return

    if md5 != r.headers['ETag'].strip('"'):
        zipFile.unlink()
        print('ETag md5sum checksum failure')
        return

    chromeDriver = _APP_DIR / 'chromedriver.exe'
    if chromeDriver.is_file():
        print(f'Removing old chromedriver {oldChromeDriverVersion}',flush=True)
        chromeDriver.unlink()

    with zipfile.ZipFile(zipFile) as zp:
        zp.extract('chromedriver.exe',path=_APP_DIR)

    if not chromeDriver.is_file():
        print(f'Extraction fail, check {zipFile}')
        return

    zipFile.unlink()

    newChromeDriverVersion = getChromeDriverVersion()
    if not oldChromeDriverVersion:
        print(f'Installed new ChromeDriver {newChromeDriverVersion}')
    elif oldChromeDriverVersion != newChromeDriverVersion:
        print(f'Chrome driver update from {oldChromeDriverVersion} to {newChromeDriverVersion}')

    print(f'DONE: {chromeDriver}')

def getSS(link,session=None,parser='html.parser'):
    ''' Returns session,soup objs'''
    s = session if session else requests.Session()
    r = s.get(link)
    if r.status_code != 200:
        raise WeebException(f'{link} {r.status_code}')
    return s, BeautifulSoup(r.content,parser)

def makeDirs(*dirs):
    for d in dirs:
        d.mkdir(parents=True,exist_ok=True)

def removeDirs(*dirs):
    for d in dirs:
        shutil.rmtree(d,ignore_errors=True)
        time.sleep(0.5)

def askQuestion(question):
    if not question.endswith(' [y/n]: '):
        question += ' [y/n]: '
    ans = ''
    while ans.lower() not in {'y','n'}:
        ans = input(question)
    return ans.lower()

def getJsonData(jFile):
    if not jFile.is_file():
        return {}
    with open(jFile) as f:
        return json.load(f)

def writeJsonData(jData,jFile):
    with open(jFile,'w') as f:
        json.dump(jData,f,indent=4)

def sanitize(x):
    return re.sub(r'[\\/:*?"<>|]','_',x).strip('.')
