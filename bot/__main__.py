import time
from sys import executable

from telegram import ParseMode, update
from telegram.error import BadRequest, TimedOut
from telegram.ext import (CallbackContext, CommandHandler, Filters,
                          MessageHandler, run_async)

from bot import *
from bot.bot_commands import BotCommands
from bot.clone_status import CloneStatus
from bot.decorators import is_authorised, is_owner
from bot.fs_utils import (get_readable_file_size, get_readable_time,
                          is_gdrive_link)
from bot.gDrive import *
from bot.msg_utils import deleteMessage, sendMessage
from bot import update


@run_async
def start(update, context):
    uptime = get_readable_time(time.time() - botStartTime)
    LOGGER.info('UID: {} - UN: {} - MSG: {}'.format(update.message.chat.id,
                update.message.chat.username, update.message.text))
    if update.message.chat.id in AUTHORISED_USERS or update.message.from_user.id == OWNER_ID:
        start_string = f'''Hey Please send me a Google Drive Shareable Link to Clone to your Drive\n\nSend /{BotCommands.HelpCommand} for checking all available commands\n\n*I'm Alive Since :  {uptime} \n\n ✯ Also Read the Important Instructions by clicking the Instructions Button in Help  !!'''
        sendMessage(start_string, context.bot, update)
    else:
        sendMessage(
            'Oops! not a Authorized user.\nPlease deploy your own <b> Clone bot</b>.', context.bot, update)

    # ;-;


@run_async
def helper(update, context):
    sendMessage("Here are the available commands of the bot\n\n"
                "You can also send Link without any command in Bot pm\n"
                f"*Usage:* `/{BotCommands.CloneCommand}: To get this message <link> [DESTINATION_ID]`\n*Example:* \n1. `/{BotCommands.CloneCommand}: To get this message https://drive.google.com/drive/u/1/folders/0AO-ISIXXXXXXXXXXXX`\n2. `/clone 0AO-ISIXXXXXXXXXXXX`"
                "\n*DESTIONATION_ID* is optional. It can be either link or ID to where you wish to store a particular clone."
                "\n\nYou can also *ignore folders* from clone process by doing the following:\n"
                f"`/{BotCommands.CloneCommand}: To get this message <FOLDER_ID> [DESTINATION] [id1,id2,id3]`\n In this example: id1, id2 and id3 would get ignored from cloning\nDo not use <> or [] in actual message."
                "*Make sure to not put any space between commas (,).*", context.bot, update, 'Markdown')

# TODO Cancel Clones with /cancel command.
# Maybe add GDTOT SUPPORT

@run_async
@is_authorised
def cloneNode(update, context):
    args = update.message.text.split(" ")
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
            # Usage: /clone <FolderToClone> <Destination> <IDtoIgnoreFromClone>,<IDtoIgnoreFromClone>

        msg = sendMessage(
            f"<b> Cloning:</b> <code>{link}</code>", context.bot, update)
        status_class = CloneStatus()
        gd = GoogleDriveHelper(GFolder_ID=DESTINATION_ID)
        sendCloneStatus(update, context, status_class, msg, link)
        result = gd.clone(link, status_class, ignoreList=ignoreList)
        deleteMessage(context.bot, msg)
        status_class.set_status(True)
        sendMessage(result, context.bot, update)
    else:
        sendMessage("Provide a Google Drive Shared Link to Clone.", bot, update)


@run_async
@is_authorised
def pvtclone(update, context):
    args = update.message.text.split(" ")
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

        msg = sendMessage(
            f"<b>📲 Cloning:</b> <code>{link}</code>", context.bot, update)
        status_class = CloneStatus()
        gd = GoogleDriveHelper(GFolder_ID=DESTINATION_ID)
        sendCloneStatus(update, context, status_class, msg, link)
        result = gd.clone(link, status_class, ignoreList=ignoreList)
        deleteMessage(context.bot, msg)
        status_class.set_status(True)
        sendMessage(result, context.bot, update)
    else:
        sendMessage("Learn To Use me.", bot, update)


@run_async
def sendCloneStatus(update, context, status, msg, link):
    old_text = ''
    while not status.done():
        sleeper(3)
        try:
            if update.message.from_user.username:
                uname = f'@{update.message.from_user.username}'
            else:
                uname = f'<a href="tg://user?id={update.message.from_user.id}">{update.message.from_user.first_name}</a>'
            text = f'🔗 *Cloning:* [{status.MainFolderName}]({status.MainFolderLink})\n━━━━━━━━━━━━━━\n' \
                f'🗃️ *Current File:* `{status.get_name()}`\n📚 *Total File:* `{int(len(status.get_name()))}`\n' \
                f'⬆️ *Transferred*: `{status.get_size()}`\n📁 *Destination:* [{status.DestinationFolderName}]({status.DestinationFolderLink})\n\n' \
                f'*👤 Clone by: {uname} ID:* `{update.message.from_user.id}`'

            if status.checkFileStatus():
                text += f"\n🕒 <b>Checking Existing Files:</b> {str(status.checkFileStatus())}"
            if not text == old_text:
                msg.edit_text(text=text, parse_mode="Markdown", timeout=200)
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


@run_async
@is_owner
def sendLogs(update, context):
    with open('log.txt', 'rb') as f:
        bot.send_document(document=f, filename=f.name,
                          reply_to_message_id=update.message.message_id,
                          chat_id=update.message.chat_id)


@run_async
@is_owner
def deletefile(update, context):
    msg_args = update.message.text.split(None, 1)
    msg = ''
    try:
        link = msg_args[1]
        LOGGER.info(link)
    except IndexError:
        msg = 'Send a link along with command'

    if not msg:
        drive = GoogleDriveHelper()
        msg = drive.deletefile(link)
    LOGGER.info(f"DeleteFileCmd: {msg}")
    reply_message = sendMessage(msg, context.bot, update)


@run_async
@is_owner
def restart(update, context):
    restart_message = sendMessage(
        "Restarting, Please wait!", context.bot, update)
    # Save restart message object in order to reply to it after restarting
    with open(".restartmsg", "w") as f:
        f.truncate(0)
        f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
    os.execl(executable, executable, "-m", "bot")


botcmds = [
    (f'{BotCommands.CloneCommand}', 'Start Clone'),
    (f'{BotCommands.LogCommand}', 'Send log'),
    (f'{BotCommands.DeleteCommand}', 'Delete file'),
    (f'{BotCommands.HelpCommand}', 'help')
]

bot.set_my_commands(botcmds)


def main():
    LOGGER.info("📶 Bot Started!")
    if os.path.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        bot.edit_message_text("𝐁𝐨𝐭 𝐑𝐞𝐬𝐭𝐚𝐫𝐭𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲!", chat_id, msg_id)
        os.remove(".restartmsg")

    bot.sendMessage(
        chat_id=OWNER_ID,
        text="<b>Bot Started Successfully!</b>",
        parse_mode=ParseMode.HTML,
    )

    try:
        for i in AUTHORISED_USERS:
            bot.sendMessage(
                chat_id=i,
                text='<b>Bot Started Successfully!</b>',
                parse_mode=ParseMode.HTML,
            )

    except Exception:
        pass

    clone_handler = CommandHandler(f'{BotCommands.CloneCommand}', cloneNode)
    start_handler = CommandHandler(f'{BotCommands.StartCommand}', start)
    help_handler = CommandHandler(f'{BotCommands.HelpCommand}', helper)
    log_handler = CommandHandler(f'{BotCommands.LogCommand}', sendLogs)
    delete_handler = CommandHandler(f'{BotCommands.DeleteCommand}', deletefile)
    restart_handler = CommandHandler(f'{BotCommands.RestartCommand}', restart)
    dispatcher.add_handler(log_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(clone_handler)
    dispatcher.add_handler(MessageHandler(
        Filters.text & Filters.private & ~Filters.command, pvtclone))
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(delete_handler)
    dispatcher.add_handler(restart_handler)
    updater.start_polling()


main()
