"""OWNER ONLY COMMANDS"""
import os
import subprocess
from sys import executable
from pyrogram.client import Client
from pyrogram import filters
from bot.bot_commands import BotCommands
from bot import AUTHORISED_USERS, OWNER_ID


@Client.on_message(filters.command(BotCommands.LogCommand))
async def sendLogs(bot, message):
    if message.from_user.id in AUTHORISED_USERS or message.from_user.id == OWNER_ID:    # noqa
        with open('log.txt', 'rb') as f:
            await bot.send_document(document=f, caption=f.name,
                                    reply_to_message_id=message.id,
                                    chat_id=message.chat.id)


@Client.on_message(filters.command(BotCommands.RestartCommand))
async def restart(bot, message):
    if message.from_user.id in AUTHORISED_USERS or message.from_user.id == OWNER_ID:    # noqa
        restart_message = await message.reply_text(
            "Restarting, Please wait!")
        # Save restart message object in order to reply to it after restarting
        with open(".restartmsg", "w") as f:
            f.truncate(0)
            f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
        os.execl(executable, executable, "-m", "bot")


@Client.on_message(filters.command(BotCommands.UpdateCommand))
async def gitpull(bot, message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        out = subprocess.check_output(["git", "pull"]).decode("UTF-8")
        if "Already up to date." in str(out):
            return await message.reply_text("Its already up-to date !🙄")
        await message.reply_text(f"<code>{out}</code>")  # Changelog
        restart_message = await message.reply_text(
            'Updated with default branch, restarting now.')

        with open(".restartmsg", "w") as f:
            f.truncate(0)
            f.write(
                f"{restart_message.chat.id}\n{restart_message.message.id}\n")
        os.execl(executable, executable, "-m", "bot")
    except Exception as e:
        await message.reply_text(f'<b>ERROR :</b> <code>{e}</code>')
