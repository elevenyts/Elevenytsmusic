"""Very small MongoDB wrapper — just enough to remember which chats
have used the bot, so /broadcast has somewhere to send to."""

from pymongo import MongoClient

import config

mongo = MongoClient(config.MONGO_URL)
db = mongo["ArtistMusicSimple"]
chats = db["chats"]


def add_served_chat(chat_id: int) -> None:
    chats.update_one({"chat_id": chat_id}, {"$set": {"chat_id": chat_id}}, upsert=True)


def remove_served_chat(chat_id: int) -> None:
    chats.delete_one({"chat_id": chat_id})


def get_served_chats() -> list:
    return [doc["chat_id"] for doc in chats.find({})]
