
# Why
You Know better

## Setting up config file 
- **BOT_TOKEN** : The telegram bot token that you get from @BotFather
- **GDRIVE_FOLDER_ID** : This is the folder ID of the Google Drive Folder to which you want to clone.
- **OWNER_ID** : The Telegram user ID (not username) of the owner of the bot (if you do not have that, send /id to @kelverbot )
- **AUTHORISED_USERS** : The Telegram user IDs (not username) of people you wish to allow for bot access.It can also be group chat id. Write like: [123456, 4030394, -1003823820]
- **IS_TEAM_DRIVE** : (Optional field) Set to True if GDRIVE_FOLDER_ID is from a Team Drive else False or Leave it empty.
- **USE_SERVICE_ACCOUNTS**: (Optional field) (Leave empty if unsure) Whether to use service accounts or not. For this to work see  "Using service accounts" section below.
- **INDEX_URL** : (Optional field) Refer to [Bhadoo Index](https://gitlab.com/ParveenBhadooOfficial/Google-Drive-Index) The URL should not have any trailing '/'
- **ACCOUNTS_ZIP_URL** :Only if you want to load your Service Account externally from an Index Link. Archive the accounts folder to a zip file. Fill this with the direct link of that file.
- **TOKEN_PICKLE_URL** :Only if you want to load your **token.pickle** externally from an Index Link. Fill this with the direct link of that file. If  you don't know how to create token.pickle

## Getting Google OAuth API credential file

- Visit the [Google Cloud Console](https://console.developers.google.com/apis/credentials)
- Go to the OAuth Consent tab, fill it, and save.
- Go to the Credentials tab and click Create Credentials -> OAuth Client ID
- Choose Other and Create.
- Use the download button to download your credentials.
- Move that file to the root of clone-bot, and rename it to credentials.json
- Visit [Google API page](https://console.developers.google.com/apis/library)
- Search for Drive and enable it if it is disabled
- Finally, run the script to generate token file (token.pickle) for Google Drive:
```
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
python3 generate_drive_token.py
```
# Running
## To run this bot (locally) (suggested)
```
python3 -m bot
```

**Tip: Instead of using Termux or local machine, use [repl.it](https://repl.it/), atleast it won't throw any errors in installing Python requirements. From [repl.it](https://repl.it/) you could push to a private GitHub repo and attach that to Heroku.**


### Using service accounts for uploading to avoid user rate limit
For Service Account to work, you must set USE_SERVICE_ACCOUNTS=True in config file or environment variables
Many thanks to [AutoRClone](https://github.com/xyou365/AutoRclone) for the scripts

## Generating service accounts
Step 1. Generate service accounts [What is service account](https://cloud.google.com/iam/docs/service-accounts)
---------------------------------
Let us create only the service accounts that we need. 
**Warning:** abuse of this feature is not the aim of autorclone and we do **NOT** recommend that you make a lot of projects, just one project and 100 sa allow you plenty of use, its also possible that overabuse might get your projects banned by google. 

```
Note: 1 service account can copy around 750gb a day, 1 project makes 100 service accounts so thats 75tb a day, for most users this should easily suffice. 
```

`python3 gen_sa_accounts.py --quick-setup 1 --new-only`

A folder named accounts will be created which will contain keys for the service accounts created

NOTE: If you have created SAs in past from this script, you can also just re download the keys by running:
```
python3 gen_sa_accounts.py --download-keys project_id
```

### Add all the service accounts to the Team Drive or folder
- Run:
```
python3 add_to_team_drive.py -d SharedTeamDriveSrcID
```

### Guide  
- YouTube Guide: [Google Drive Clone Bot Set-Up Tutorial | Telegram Bot Setup Guide](https://www.youtube.com/watch?v=2r3_jR7SvUo&feature=youtu.be)
  - Follow the above guide for Heroku.
  - If you wish to run on a VPS, Do all the stuff I did on the VPS Terminal ;) 
  - Wish to run anywhere else? Follow the guide till the part where I download ZIP Archive from Repl.it. Use that zip on any device you'd like to run the bot on. 
  - Don't forget to install requirements.txt
    ```
    pip3 install -r requirements.txt
    ```
- [Adding Service Accounts to Google Group/TeamDrive](https://youtu.be/pBfsmJhYr78)

## Docker Guide

Deploying is pretty much straight forward and is divided into several steps as follows:
### Installing requirements

- Clone this repo:
```
git clone https://github.com/zekxtreme/CLONE-HUNTER/
cd CLONE-HUNTER
```

- Install requirements
For Debian based distros
```
sudo apt install python3
```
Install Docker by following the [official Docker docs](https://docs.docker.com/engine/install/debian/)

OR
```
sudo snap install docker 
```
- For Arch and it's derivatives:
```
sudo pacman -S docker python
```

Fill up the `config.env` then
    
- Start Docker daemon (skip if already running):
```
sudo dockerd
```
- Build Docker image:
```
docker build . --rm --force-rm --compress --no-cache=true --pull --file Dockerfile -t clonebot
```
- Run the image:
```
sudo docker run clonebot
```
  
- To stop Docker run 
```
sudo docker ps
sudo docker stop id
```

### Credits
- [jagarit007](https://github.com/jagrit007) for base repo and guide
- [Izzy](https://github.com/lzzy12/python-aria-mirror-bot)
- [xyou365](https://github.com/xyou365/AutoRclone)
