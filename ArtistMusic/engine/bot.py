"""Core clients: the bot, the assistant userbot that joins voice chats,
and the PyTgCalls instance."""

from pyrogram import Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pytgcalls import PyTgCalls

import config

app = Client(
    "ArtistMusicSimpleBot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
)

userbot = Client(
    "ArtistMusicSimpleAssistant",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
)

calls = PyTgCalls(userbot)


def player_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏸", callback_data="cb_pause"),
                InlineKeyboardButton("▶️", callback_data="cb_resume"),
                InlineKeyboardButton("⏭", callback_data="cb_skip"),
                InlineKeyboardButton("⏹", callback_data="cb_stop"),
            ]
        ]
    )
