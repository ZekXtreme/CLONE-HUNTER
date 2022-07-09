import time
from pyrogram.client import Client
from pyrogram import enums, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.fs_utils import get_readable_time
from bot import botStartTime, LOGGER, AUTHORISED_USERS, OWNER_ID
from bot.bot_commands import BotCommands


@Client.on_message(filters.command(BotCommands.StartCommand))
async def start(bot, message):
    uptime = get_readable_time(time.time() - botStartTime)
    LOGGER.info('UID: {} - UN: {} - MSG: {}'.format(message.chat.id,
                message.from_user.mention, message.text))
    if message.chat.id in AUTHORISED_USERS or message.from_user.id == OWNER_ID:
        start_string = f'''
Hey Please send me a Drive Shareable Link to Clone to your Drive
Send /{BotCommands.HelpCommand} for checking all available commands
I'm Alive Since :  {uptime} Also Read the Important
Instructions by clicking the Instructions in Help  !!'''
        await message.reply_text(start_string, reply_markup=START_BUTTONS)
    else:
        await message.reply_text('''Oops! not a Authorized user.
               Please deploy your own <b>Clone bot</b>''')


START_BUTTONS = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton('Help', callback_data='help'),
            InlineKeyboardButton('Close', callback_data='close')
        ]
    ]
)


@Client.on_message(filters.command(BotCommands.HelpCommand) & (filters.chat(AUTHORISED_USERS) | filters.user(OWNER_ID)))  # noqa
async def help(bot, message):
    await message.reply_text(HELP_TEXT, disable_web_page_preview=True,
                             parse_mode=enums.ParseMode.HTML)


HELP_TEXT = f"""<br>
<b>/{BotCommands.HelpCommand}</b>: To get this message
<br><br>
<b>/{BotCommands.CloneCommand}</b> [url / ID]: Copy file/folder to Google Drive
<br><br>
You can also send Link without any command in Bot pm
<br><br>
You can also Check Example <a href="https://rentry.co/clonehelp">Here</a>"""


@Client.on_callback_query()
async def cb_handler(bot, message):
    if message.data == "help":
        await message.message.edit_text(
            text=HELP_TEXT,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True
        )

    elif message.data == "close":
        await message.message.delete()
