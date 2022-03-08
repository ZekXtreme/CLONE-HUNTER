import json
import logging
import os
import subprocess
import time
from distutils.util import strtobool as stb

import requests
import telegram.ext as tg
from dotenv import load_dotenv

from bot import *

CONFIG_FILE_URL = os.environ.get('CONFIG_FILE_URL', None)
if CONFIG_FILE_URL is not None:
    res = requests.get(CONFIG_FILE_URL)
    if res.status_code == 200:
        with open('config.env', 'wb+') as f:
            f.write(res.content)
            f.close()
    else:
        logging.error(res.status_code)

load_dotenv('config.env')

botStartTime = time.time()
if os.path.exists('log.txt'):
    with open('log.txt', 'r+') as f:
        f.truncate(0)

def getConfig(name: str):
    return os.environ[name]


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(
                        'log.txt'), logging.StreamHandler()],
                    level=logging.INFO)

LOGGER = logging.getLogger(__name__)

try:
    BOT_TOKEN = getConfig('BOT_TOKEN')
    GDRIVE_FOLDER_ID = getConfig('GDRIVE_FOLDER_ID')
    OWNER_ID = int(getConfig('OWNER_ID'))
    AUTHORISED_USERS = json.loads(getConfig('AUTHORISED_USERS'))
except KeyError as e:
    LOGGER.error("One or more env variables missing! Exiting now")
    exit(1)

json.dumps(AUTHORISED_USERS)

try:
    INDEX_URL = getConfig('INDEX_URL')
    if len(INDEX_URL) == 0:
        INDEX_URL = None
except KeyError:
    INDEX_URL = None

try:
    TOKEN_PICKLE_URL = getConfig('TOKEN_PICKLE_URL')
    if len(TOKEN_PICKLE_URL) == 0:
        TOKEN_PICKLE_URL = None
    else:
        res = requests.get(TOKEN_PICKLE_URL)
        if res.status_code == 200:
            with open('token.pickle', 'wb+') as f:
                f.write(res.content)
                f.close()
        else:
            logging.error(res.status_code)
            raise KeyError
except KeyError:
    pass
try:
    ACCOUNTS_ZIP_URL = getConfig('ACCOUNTS_ZIP_URL')
    if len(ACCOUNTS_ZIP_URL) == 0:
        ACCOUNTS_ZIP_URL = None
    else:
        res = requests.get(ACCOUNTS_ZIP_URL)
        if res.status_code == 200:
            with open('accounts.zip', 'wb+') as f:
                f.write(res.content)
                f.close()
        else:
            logging.error(res.status_code)
            raise KeyError
        subprocess.run(["unzip", "-q", "-o", "accounts.zip"])
        os.remove("accounts.zip")
except KeyError:
    pass

try:
    USE_SERVICE_ACCOUNTS = getConfig('USE_SERVICE_ACCOUNTS')
    USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == 'true'
except KeyError:
    USE_SERVICE_ACCOUNTS = False

try:
    IS_TEAM_DRIVE = getConfig('IS_TEAM_DRIVE')
    IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == 'true'
except KeyError:
    IS_TEAM_DRIVE = False

LOGGER = logging.getLogger(__name__)
updater = tg.Updater(token=BOT_TOKEN, use_context=True, workers=16)
bot = updater.bot
dispatcher = updater.dispatcher
