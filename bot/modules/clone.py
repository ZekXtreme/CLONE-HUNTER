import time
from pyrogram.client import Client
from pyrogram import enums, filters
from bot import LOGGER, GDRIVE_FOLDER_ID, AUTHORISED_USERS, OWNER_ID
from bot.fs_utils import is_gdrive_link
from bot.bot_commands import BotCommands
from bot.clone_status import CloneStatus
from bot.gDrive import GoogleDriveHelper

COMMAND_FILTER = (~filters.command([BotCommands.CloneCommand, BotCommands.CountCommand, BotCommands.DeleteCommand, BotCommands.HelpCommand, BotCommands.RestartCommand, BotCommands.UpdateCommand, BotCommands.LogCommand]))

@Client.on_message(filters.command(BotCommands.CloneCommand) & (filters.chat(AUTHORISED_USERS) | filters.user(OWNER_ID)))  # noqa
async def cloneNode(bot, message):
    args = message.text.split(" ")
    if len(args) > 1:
        link = args[1]
        try:
            ignoreList = args[-1].split(',')
        except IndexError:
            ignoreList = []

        DESTINATION_ID = GDRIVE_FOLDER_ID
        try:
            DESTINATION_ID = args[2]
            print(DESTINATION_ID)
        except IndexError:
            pass
        msg = await message.reply_text(
            f"<b> Cloning:</b> <code>{link}</code>",)
        status_class = CloneStatus()
        gd = GoogleDriveHelper(GFolder_ID=DESTINATION_ID)
        # await sendCloneStatus(bot, message, status_class, msg, link)
        result = gd.clone(link, status_class, ignoreList=ignoreList)
        await msg.delete()
        status_class.set_status(True)
        await message.reply_text(result, disable_web_page_preview=True)
    else:
        await message.reply_text("Provide a Google Drive Shared Link to Clone")


async def sendCloneStatus(bot, message, status, msg, link):
    old_text = ''
    while not status.done():
        sleeper(3)
        try:
            if message.from_user.username:
                uname = f'@{message.from_user.username}'
            else:
                uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'   # noqa
            text = f'''
Cloning: [{status.MainFolderName}]({status.MainFolderLink})\n━━━━━━━━━━━━━━\n
Current File: {status.get_name()}\n Total File: {int(len(status.get_name()))}
Transferred*: `{status.get_size()}`\n Destination: [{status.DestinationFolderName}]({status.DestinationFolderLink})
Clone by: {uname} ID: {message.from_user.id}
                '''  # noqa

            if status.checkFileStatus():
                text += f"\n🕒 <b>Checking Existing Files:</b> {str(status.checkFileStatus())}"    # noqa
            if not text == old_text:
                await msg.edit_text(text=text,
                                    parse_mode=enums.ParseMode.MARKDOWN,
                                    )
                old_text = text
        except Exception as e:
            LOGGER.error(e)
            if str(e) == "Message to edit not found":
                break
            sleeper(2)
            continue
    return


def sleeper(value, enabled=True):
    time.sleep(int(value))
    return


@Client.on_message(filters.private & (filters.chat(AUTHORISED_USERS) | filters.user(OWNER_ID)) & filters.regex(r"https:\/\/drive\.google\.com\/(?:drive(.*?)\/folders\/|file(.*?)?\/d\/)([-\w]+)") & COMMAND_FILTER )  # noqa
async def pvtclone(bot, message):
    args = message.text.split(" ")
    link = args[0]
    if is_gdrive_link(link):
        try:
            ignoreList = args[-1].split(',')
        except IndexError:
            ignoreList = []

        DESTINATION_ID = GDRIVE_FOLDER_ID
        try:
            DESTINATION_ID = args[1]
            print(DESTINATION_ID)
        except IndexError:
            pass

        msg = await message.reply_text(
            f"<b> Cloning:</b> <code>{link}</code>",)
        status_class = CloneStatus()
        gd = GoogleDriveHelper(GFolder_ID=DESTINATION_ID)
        # await sendCloneStatus(bot, message, status_class, msg, link)
        result = gd.clone(link, status_class, ignoreList=ignoreList)
        await msg.delete()
        status_class.set_status(True)
        await msg.reply_text(result, disable_web_page_preview=True)
    else:
        await message.reply_text("Learn to use me :(")


@Client.on_message(filters.command(BotCommands.DeleteCommand) & filters.user(OWNER_ID))
async def deletefile(bot, message):
    msg_args = message.text.split(None, 1)
    msg = ''
    try:
        link = msg_args[1]
        LOGGER.info(link)
    except IndexError:
        msg = 'Send a link along with command'

    if msg == '':
        drive = GoogleDriveHelper()
        msg = drive.deletefile(link)
    LOGGER.info(f"DeleteFileCmd: {msg}")
    await message.reply_text(msg, disable_web_page_preview=True)


@Client.on_message(filters.command(BotCommands.CountCommand) & (filters.chat(AUTHORISED_USERS) | filters.user(OWNER_ID)))
async def countNode(bot, message):
    args = message.text.split(" ", maxsplit=1)
    if len(args) > 1:
        link = args[1]
    else:
        link = None
    if link is not None:
        msg = await message.reply_text(f"Counting: <code>{link}</code>")
        gd = GoogleDriveHelper()
        result = gd.count(link)
        if message.from_user.username:
            uname = f'@{message.from_user.username}'
        else:
            uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
        if uname is not None:
            cc = f'\n\n<b>Count by: {uname} ID:</b> <code>{message.from_user.id}</code>'
        await msg.edit_text(result + cc)
    else:
        await message.reply_text("<b>Provide G-Drive Shareable Link to Count.</b>")
