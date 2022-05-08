import os
import subprocess
from sys import executable

from telegram import BotCommand, ParseMode, update
from telegram.error import BadRequest, TimedOut
from telegram.ext import CommandHandler, run_async

from bot import *
from bot.bot_commands import BotCommands
from bot.decorators import is_owner
from bot.msg_utils import sendMessage


@run_async
@is_owner
def gitpull(update, context):
    try:
        out = subprocess.check_output(["git", "pull"]).decode("UTF-8")
        if "Already up to date." in str(out):
            return sendMessage("Its already up-to date !🙄", context.bot, update)
        sendMessage(f"<code>{out}</code>", context.bot, update)  # Changelog
        restart_message = sendMessage(
            'Updated with default branch, restarting now.',
            context.bot,
            update,
        )

        with open(".restartmsg", "w") as f:
            f.truncate(0)
            f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
        os.execl(executable, executable, "-m", "bot")
    except Exception as e:
        sendMessage(f'<b>ERROR :</b> <code>{e}</code>', context.bot, update)


update_handler = CommandHandler(f'{BotCommands.UpdateCommand}', gitpull)
dispatcher.add_handler(update_handler)
