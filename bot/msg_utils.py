from time import sleep
from telegram.message import Message
from telegram.update import Update, Bot
from telegram.error import RetryAfter

from bot import LOGGER, bot


def deleteMessage(bot: Bot, message: Message):
    try:
        bot.delete_message(chat_id=message.chat.id,
                           message_id=message.message_id)
    except Exception as e:
        LOGGER.error(str(e))


def editMessage(text: str, message: Message):
    try:
        bot.edit_message_text(text=text, message_id=message.message_id,
                              chat_id=message.chat.id,
                              parse_mode='HTMl', disable_web_page_preview=True)
    except RetryAfter as r:
        LOGGER.warning(str(r))
        sleep(r.retry_after * 1.5)
        return editMessage(text, message)
    except Exception as e:
        LOGGER.error(str(e))
        return


def sendMessage(text: str, bot: Bot, update: Update, parse_mode='HTMl'):
    return bot.send_message(update.message.chat_id,
                            reply_to_message_id=update.message.message_id,
                            text=text, parse_mode=parse_mode)


def sendLogFile(bot: Bot, update: Update):
    with open('log.txt', 'rb') as f:
        bot.send_document(
            document=f, filename=f.name,
            reply_to_message_id=update.message.message_id,
            chat_id=update.message.chat_id
        )


# To-do: One clone message for all clones; clone cancel command
