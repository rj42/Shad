#!/usr/bin/env python3
# -*- coding:utf8 -*-

# ---------------------------------------- Prerequests ------------------------------------------ #
# Install these packages before use:
#   https://github.com/python-telegram-bot/python-telegram-bot
#   https://github.com/tyrannosaurus/python-yandex-translate

import telegram
from time import sleep

from urllib.error import URLError
from yandex_translate import YandexTranslate
from yandex_translate import YandexTranslateException

# ----------------------------------------- Constants ------------------------------------------- #

TELEGRAM_TOKEN = "152476894:AAHDSPSz-fAKhyGQfJY-VQc1TVoRmSl9TYE"
YA_TRANSLATE_TOKEN = "trnsl.1.1.20151220T153628Z.6f71a683eb51f76d.09b6b005f8b007855666b2d69c9e498b0635c3f5"

def get_help_response():
    result = ("/translate LANG TEXT: translate text to language\n"
              "/langs: list of supported languages")
    return result

def get_tranlsate_response(translator, text):
    parts = text.split(' ')
    dst_lang = parts[0]
    text_to_translate = ' '.join(parts[1:])
    result = text_to_translate + " → "
    try:
        translation = translator.translate(text_to_translate, dst_lang)
        result += translation["text"][0] + " ({})".format(translation["lang"])
    except YandexTranslateException as e:
        result += str(e)
    return result

def get_supported_languages_response(translator):
    return str(translator.directions)

def get_unknown_command_response(cmd):
    return ("Unknown command: {}. Use /help to get full list of supportable commands".format(cmd))

def get_command_response(cmd, translator, text):
    if cmd == 'help':
        return get_help_response()
    elif cmd == 'translate':
        return get_tranlsate_response(translator, text)
    elif cmd == 'langs':
        return get_supported_languages_response(translator)
    else:
        return get_unknown_command_response(cmd)

def message_response(bot, translator, update_id):
    for update in bot.getUpdates(offset=update_id):
        chat_id = update.message.chat_id
        update_id = update.update_id + 1
        message = update.message.text

        if message:
            if message.startswith('/'):
                cmd = message[1:].split(' ')[0]
                text = ' '.join(message[1:].split(' ')[1:])
                bot.sendMessage(chat_id=chat_id, 
                    text=get_command_response(cmd, translator, text))
            else:
                bot.sendMessage(chat_id=chat_id, text=get_help_response())
    return update_id


def main():
    bot = telegram.Bot(TELEGRAM_TOKEN)
    translator = YandexTranslate(YA_TRANSLATE_TOKEN)

    try:
        update_id = bot.getUpdates()[0].update_id
    except IndexError:
        update_id = None

    while True:
        try:
            update_id = message_response(bot, translator, update_id)
        except telegram.TelegramError as e:
            if e.message in ("Bad Gateway", "Timed out"):
                sleep(1)
            elif e.message == "Unauthorized":
                update_id += 1
            else:
                raise e
        except URLError as e:
            sleep(1)


if __name__ == '__main__':
    main()
