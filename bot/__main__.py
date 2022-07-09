import os
from pyrogram.client import Client
from pyrogram import __version__
from pyrogram.types import BotCommand
from pyrogram.raw.all import layer
from .bot_commands import BotCommands
from . import LOGGER, API_ID, API_HASH, BOT_TOKEN


plugins = dict(
    root="bot/modules"
)

botcmds = [
    BotCommand(f'{BotCommands.CloneCommand}', 'Start Clone'),
    BotCommand(f'{BotCommands.LogCommand}', 'Send log'),
    BotCommand(f'{BotCommands.DeleteCommand}', 'Delete file'),
    BotCommand(f'{BotCommands.HelpCommand}', 'help')
]


class Bot(Client):
    def __init__(self):
        super().__init__(
            "clonebot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=plugins
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        un = '@' + me.username
        if os.path.isfile(".restartmsg"):
            with open(".restartmsg") as f:
                chat_id, msg_id = map(int, f)
            await self.edit_message_text(chat_id=chat_id, message_id=msg_id,
                                         text="Restarted Succesfully")
            os.remove(".restartmsg")
        await self.set_bot_commands(botcmds)

        LOGGER.info(
            f"Pyrogram v{__version__} (Layer {layer}) started on {un}.")

    async def stop(self, *args):
        await self.delete_bot_commands()
        await super().stop()
        LOGGER.info('Bot Stopped!')


if __name__ == "__main__":
    app = Bot()
    app.run()
