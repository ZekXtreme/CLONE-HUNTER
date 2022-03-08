import json
import logging
import os
import pickle
import random
import re
import socket
import urllib.parse as urlparse
from urllib.parse import parse_qs

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from tenacity import *

from bot import *
from bot import LOGGER
from bot.fs_utils import get_mime_type

logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)
# https://github.com/googleapis/google-api-python-client/issues/632#issuecomment-541973021
socket.setdefaulttimeout(650)

try:
    if USE_SERVICE_ACCOUNTS:
        SERVICE_ACCOUNT_INDEX = random.randrange(len(os.listdir("accounts")))
except FileNotFoundError:
    USE_SERVICE_ACCOUNTS = False
    LOGGER.info('Failed To Load Accounts Folder')


def clean_name(name):
    name = name.replace("'", "\\'")
    return name


class GoogleDriveHelper:
    def __init__(self, name=None, listener=None, GFolder_ID=GDRIVE_FOLDER_ID):
        self.__G_DRIVE_TOKEN_FILE = "token.pickle"
        # Check https://developers.google.com/drive/scopes for all available scopes
        self.__OAUTH_SCOPE = ['https://www.googleapis.com/auth/drive']
        # Redirect URI for installed apps, can be left as is
        self.__REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
        self.__G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
        self.__G_DRIVE_BASE_DOWNLOAD_URL = "https://drive.google.com/uc?id={}&export=download"
        self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL = "https://drive.google.com/drive/folders/{}"
        self.__listener = listener
        self.__service = self.authorize()
        self.__listener = listener
        self._file_uploaded_bytes = 0
        self.uploaded_bytes = 0
        self.UPDATE_INTERVAL = 5
        self.start_time = 0
        self.total_time = 0
        self._should_update = True
        self.is_uploading = True
        self.is_cancelled = False
        self.status = None
        self.updater = None
        self.name = name
        self.update_interval = 3
        self.sa_count = 0
        self.alt_auth = False
        self.gparentid = self.getIdFromUrl(GFolder_ID)

    def cancel(self):
        self.is_cancelled = True
        self.is_uploading = False

    def speed(self):
        """
        It calculates the average upload speed and returns it in bytes/seconds unit
        :return: Upload speed in bytes/second
        """
        try:
            return self.uploaded_bytes / self.total_time
        except ZeroDivisionError:
            return 0

    @staticmethod
    def getIdFromUrl(link: str):
        if len(link) in {33, 19}:
            return link
        if "folders" in link or "file" in link:
            regex = r"https://drive\.google\.com/(drive)?/?u?/?\d?/?(mobile)?/?(file)?(folders)?/?d?/(?P<id>[-\w]+)[?+]?/?(w+)?"
            res = re.search(regex, link)
            if res is None:
                raise IndexError("GDrive ID not found.")
            return res.group('id')
        parsed = urlparse.urlparse(link)
        return parse_qs(parsed.query)['id'][0]

    def deletefile(self, link: str):
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Google Drive ID could not be found in the provided link"
            return msg
        msg = ''
        try:
            res = self.__service.files().delete(
                fileId=file_id, supportsTeamDrives=IS_TEAM_DRIVE).execute()
            msg = "Successfully deleted"
            LOGGER.info(f"Delete Result: {msg}")
        except HttpError as err:
            if "File not found" in str(err):
                msg = "No such file exist"
            elif "insufficientFilePermissions" in str(err):
                msg = "Insufficient File Permissions"
                token_service = self.alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.deletefile(link)
            else:
                msg = str(err)
            LOGGER.error(f"Delete Result: {msg}")
        finally:
            return msg

    def switchServiceAccount(self):
        global SERVICE_ACCOUNT_INDEX
        service_account_count = len(os.listdir("accounts"))
        if SERVICE_ACCOUNT_INDEX == service_account_count - 1:
            SERVICE_ACCOUNT_INDEX = 0
        SERVICE_ACCOUNT_INDEX += 1
        LOGGER.info(
            f"Switching to {SERVICE_ACCOUNT_INDEX}.json service account")
        self.__service = self.authorize()

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(15),
           retry=retry_if_exception_type(HttpError), before=before_log(LOGGER, logging.DEBUG))
    def __set_permission(self, drive_id):
        permissions = {
            'role': 'reader',
            'type': 'anyone',
            'value': None,
            'withLink': True
        }
        return self.__service.permissions().create(supportsTeamDrives=True, fileId=drive_id,
                                                   body=permissions).execute()

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(15),
           retry=retry_if_exception_type(HttpError), before=before_log(LOGGER, logging.DEBUG))
    def copyFile(self, file_id, dest_id, status):
        body = {
            'parents': [dest_id]
        }

        try:
            return self.__service.files().copy(supportsAllDrives=True,
                                              fileId=file_id, body=body).execute()
        except HttpError as err:
            if err.resp.get('content-type', '').startswith('application/json'):
                reason = json.loads(err.content).get(
                    'error').get('errors')[0].get('reason')
                if reason not in ['userRateLimitExceeded', 'dailyLimitExceeded']:
                    raise err
                if USE_SERVICE_ACCOUNTS:
                    self.switchServiceAccount()
                    LOGGER.info(f"Got: {reason}, Trying Again.")
                    self.copyFile(file_id, dest_id, status)

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
           retry=retry_if_exception_type(HttpError), before=before_log(LOGGER, logging.DEBUG))
    def getFilesByFolderId(self, folder_id):
        page_token = None
        q = f"'{folder_id}' in parents"
        files = []
        while True:
            response = self.__service.files().list(supportsTeamDrives=True,
                                                   includeTeamDriveItems=True,
                                                   q=q,
                                                   spaces='drive',
                                                   pageSize=200,
                                                   fields='nextPageToken, files(id, name, mimeType,size)', corpora='allDrives', orderBy='folder, name',
                                                   pageToken=page_token).execute()
            files.extend(iter(response.get('files', [])))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        return files

    def clone(self, link, status, ignoreList=[]):
        self.transferred_size = 0
        self.total_files = 0
        self.total_folders = 0
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Google drive ID could not be found in the provided link"
            return msg
        msg = ""
        LOGGER.info(f"File ID: {file_id}")
        try:
            meta = self.__service.files().get(supportsAllDrives=True, fileId=file_id,
                                              fields="name,id,mimeType,size").execute()
            dest_meta = self.__service.files().get(supportsAllDrives=True, fileId=self.gparentid,
                                                   fields="name,id,size").execute()
            status.SetMainFolder(
                meta.get('name'), self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(meta.get('id')))
            status.SetDestinationFolder(dest_meta.get(
                'name'), self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dest_meta.get('id')))
        except Exception as e:
            return f"{str(e).replace('>', '').replace('<', '')}"
        if meta.get("mimeType") == self.__G_DRIVE_DIR_MIME_TYPE:
            dir_id = self.check_folder_exists(meta.get('name'), self.gparentid)
            if not dir_id:
                dir_id = self.create_directory(
                    meta.get('name'), self.gparentid)
            try:
                self.cloneFolder(meta.get('name'), meta.get(
                    'name'), meta.get('id'), dir_id, status, ignoreList)
            except Exception as e:
                if isinstance(e, RetryError):
                    LOGGER.info(
                        f"Total Attempts: {e.last_attempt.attempt_number}")
                    err = e.last_attempt.exception()
                else:
                    err = str(e).replace('>', '').replace('<', '')
                LOGGER.error(err)
                return err
            status.set_status(True)
            msg += f'<b>Filename: </b><code>{meta.get("name")}</code>\n<b>Size: </b><code>{get_readable_file_size(self.transferred_size)}</code>'
            msg += '\n<b>Type : </b>Folder'
            msg += f"\n<b>SubFolders : </b>{self.total_folders}"
            msg += f"\n<b>Files : </b>{self.total_files}"
            msg += f'\n\n<a href="{self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id)}">☁️ G-Drive Link ☁️</a>'
            if INDEX_URL:
                url = requests.utils.requote_uri(
                    f'{INDEX_URL}/{meta.get("name")}/')
                msg += f' | <a href="{url}">🔗 Index Link 🔗</a>'
        else:
            try:
                file = self.check_file_exists(meta.get('id'), self.gparentid)
                if file:
                    status.checkFileExist(True)
                if not file:
                    status.checkFileExist(False)
                    file = self.copyFile(
                        meta.get('id'), self.gparentid, status)
            except Exception as e:
                if isinstance(e, RetryError):
                    LOGGER.info(
                        f"Total Attempts: {e.last_attempt.attempt_number}")
                    err = e.last_attempt.exception()
                else:
                    err = str(e).replace('>', '').replace('<', '')
                LOGGER.error(err)
                return err
            try:
                typeee = file.get('mimeType')
            except:
                typeee = 'File'
            msg += f'<b>Filename: </b><code>{file.get("name")}</code>'
            try:
                msg += f'\n<b>Size: </b><code>{get_readable_file_size(int(meta.get("size")))}</code>'
                msg += f'\n<b>Type : </b>{typeee}'
                msg += f'\n\n<a href="{self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file.get("id"))}">☁️ G-Drive Link ☁️</a>'
                if INDEX_URL is not None:
                    url = requests.utils.requote_uri(
                        f'{INDEX_URL}/{file.get("name")}')
                    msg += f' | <a href="{url}">🔗 Index Link 🔗</a>'
            except TypeError:
                pass
        return msg

    def cloneFolder(self, name, local_path, folder_id, parent_id, status, ignoreList=[]):
        page_token = None
        q = f"'{folder_id}' in parents"
        files = []
        LOGGER.info(f"Syncing: {local_path}")
        while True:
            response = self.__service.files().list(supportsTeamDrives=True,
                                                   includeTeamDriveItems=True,
                                                   q=q,
                                                   spaces='drive',
                                                   fields='nextPageToken, files(id, name, mimeType,size)',
                                                   pageToken=page_token).execute()
            files.extend(iter(response.get('files', [])))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        if not files:
            return parent_id
        for file in files:
            if file.get('mimeType') == self.__G_DRIVE_DIR_MIME_TYPE:
                self.total_folders += 1
                file_path = os.path.join(local_path, file.get('name'))
                current_dir_id = self.check_folder_exists(
                    file.get('name'), parent_id)
                if not current_dir_id:
                    current_dir_id = self.create_directory(
                        file.get('name'), parent_id)
                if str(file.get('id')) not in ignoreList:
                    self.cloneFolder(file.get('name'), file_path, file.get(
                        'id'), current_dir_id, status, ignoreList)
                else:
                    LOGGER.info("Ignoring FolderID from clone: " +
                                str(file.get('id')))
            else:
                try:
                    if not self.check_file_exists(file.get('name'), parent_id):
                        status.checkFileExist(False)
                        self.copyFile(file.get('id'), parent_id, status)
                        self.total_files += 1
                        self.transferred_size += int(file.get('size'))
                        status.set_name(file.get('name'))
                        status.add_size(int(file.get('size')))
                    else:
                        status.checkFileExist(True)
                except TypeError:
                    pass
                except Exception as e:
                    if isinstance(e, RetryError):
                        LOGGER.info(
                            f"Total Attempts: {e.last_attempt.attempt_number}")
                        err = e.last_attempt.exception()
                    else:
                        err = e
                    LOGGER.error(err)

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(15),
           retry=retry_if_exception_type(HttpError), before=before_log(LOGGER, logging.DEBUG))
    def create_directory(self, directory_name, parent_id):
        file_metadata = {
            "name": directory_name,
            "mimeType": self.__G_DRIVE_DIR_MIME_TYPE
        }
        if parent_id is not None:
            file_metadata["parents"] = [parent_id]
        file = self.__service.files().create(
            supportsTeamDrives=True, body=file_metadata).execute()
        file_id = file.get("id")
        if not IS_TEAM_DRIVE:
            self.__set_permission(file_id)
        LOGGER.info(
            "Created Google-Drive Folder:\nName: {}\nID: {} ".format(file.get("name"), file_id))
        return file_id

    def authorize(self):
        # Get credentials
        credentials = None
        if not USE_SERVICE_ACCOUNTS:
            if os.path.exists(self.__G_DRIVE_TOKEN_FILE):
                with open(self.__G_DRIVE_TOKEN_FILE, 'rb') as f:
                    credentials = pickle.load(f)
            if credentials is None or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', self.__OAUTH_SCOPE)
                    LOGGER.info(flow)
                    credentials = flow.run_console(port=0)

                # Save the credentials for the next run
                with open(self.__G_DRIVE_TOKEN_FILE, 'wb') as token:
                    pickle.dump(credentials, token)
        else:
            LOGGER.info(
                f"Authorizing with {SERVICE_ACCOUNT_INDEX}.json service account")
            credentials = service_account.Credentials.from_service_account_file(
                f'accounts/{SERVICE_ACCOUNT_INDEX}.json',
                scopes=self.__OAUTH_SCOPE)
        return build('drive', 'v3', credentials=credentials, cache_discovery=False)

    def alt_authorize(self):
        credentials = None
        if USE_SERVICE_ACCOUNTS and not self.alt_auth:
            self.alt_auth = True
            if os.path.exists(self.__G_DRIVE_TOKEN_FILE):
                LOGGER.info("Authorize with token.pickle")
                with open(self.__G_DRIVE_TOKEN_FILE, 'rb') as f:
                    credentials = pickle.load(f)
                if credentials is None or not credentials.valid:
                    if credentials and credentials.expired and credentials.refresh_token:
                        credentials.refresh(Request())
                    else:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'credentials.json', self.__OAUTH_SCOPE)
                        LOGGER.info(flow)
                        credentials = flow.run_console(port=0)
                    # Save the credentials for the next run
                    with open(self.__G_DRIVE_TOKEN_FILE, 'wb') as token:
                        pickle.dump(credentials, token)
                return build('drive', 'v3', credentials=credentials, cache_discovery=False)
        return None

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(15),
           retry=retry_if_exception_type(HttpError), before=before_log(LOGGER, logging.DEBUG))
    def check_folder_exists(self, fileName, u_parent_id):
        fileName = clean_name(fileName)
        # Create Search Query for API request.
        query = f"'{u_parent_id}' in parents and (name contains '{fileName}' and trashed=false)"
        response = self.__service.files().list(supportsTeamDrives=True,
                                               includeTeamDriveItems=True,
                                               q=query,
                                               spaces='drive',
                                               pageSize=5,
                                               fields='files(id, name, mimeType, size)',
                                               orderBy='modifiedTime desc').execute()
        for file in response.get('files', []):
            # Detect Whether Current Entity is a Folder or File.
            if file.get('mimeType') == "application/vnd.google-apps.folder":
                return file.get('id')

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(15),
           retry=retry_if_exception_type(HttpError), before=before_log(LOGGER, logging.DEBUG))
    def check_file_exists(self, fileName, u_parent_id):
        fileName = clean_name(fileName)
        # Create Search Query for API request.
        query = f"'{u_parent_id}' in parents and (name contains '{fileName}' and trashed=false)"
        response = self.__service.files().list(supportsTeamDrives=True,
                                               includeTeamDriveItems=True,
                                               q=query,
                                               spaces='drive',
                                               pageSize=5,
                                               fields='files(id, name, mimeType, size)',
                                               orderBy='modifiedTime desc').execute()
        for file in response.get('files', []):
            if file.get('mimeType') != "application/vnd.google-apps.folder":
                # driveid = file.get('id')
                return file

    def count(self, link):
        self.total_bytes = 0
        self.total_files = 0
        self.total_folders = 0
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Google drive ID could not be found in the provided link"
            return msg
        msg = ""
        LOGGER.info(f"File ID: {file_id}")
        try:
            drive_file = self.__service.files().get(fileId=file_id, fields="id, name, mimeType, size",
                                                    supportsTeamDrives=True).execute()
            name = drive_file['name']
            LOGGER.info(f"Counting: {name}")
            if drive_file['mimeType'] == self.__G_DRIVE_DIR_MIME_TYPE:
                self.gDrive_directory(**drive_file)
                msg += f'<b>Filename : </b><code>{name}</code>'
                msg += f'\n<b>Size : </b>{get_readable_file_size(self.total_bytes)}'
                msg += '\n<b>Type : </b>Folder'
                msg += f"\n<b>SubFolders : </b>{self.total_folders}"
                msg += f"\n<b>Files : </b>{self.total_files}\n\n"
            else:
                msg += f'<b>Filename : </b><code>{name}</code>'
                try:
                    typee = drive_file['mimeType']
                except:
                    typee = 'File'
                try:
                    self.total_files += 1
                    self.gDrive_file(**drive_file)
                    msg += f'\n<b>Size : </b><code>{get_readable_file_size(self.total_bytes)}</code>'
                    msg += f"\n<b>Type : </b>{typee}"
                    msg += f"\n<b>Files : </b>{self.total_files}\n\n"
                except TypeError:
                    pass
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(
                    f'Total Attempts: {err.last_attempt.attempt_number}')
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            LOGGER.error(err)
            return err
        return msg

    def gDrive_file(self, **kwargs):
        try:
            size = int(kwargs['size'])
        except:
            size = 0
        self.total_bytes += size

    def gDrive_directory(self, **kwargs) -> None:
        files = self.getFilesByFolderId(kwargs['id'])
        if len(files) == 0:
            return
        for file_ in files:
            if file_['mimeType'] == self.__G_DRIVE_DIR_MIME_TYPE:
                self.total_folders += 1
                self.gDrive_directory(**file_)
            else:
                self.total_files += 1
                self.gDrive_file(**file_)


def get_readable_file_size(size_in_bytes) -> str:
    SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024:
        size_in_bytes /= 1024
        index += 1
    try:
        return f'{round(size_in_bytes, 2)}{SIZE_UNITS[index]}'
    except IndexError:
        return 'File too large'
