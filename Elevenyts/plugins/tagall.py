# Elevenyts/plugins/tagall.py
# FINAL WORKING VERSION - NO ERRORS

import asyncio
import random
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus

logger = logging.getLogger(__name__)

# =========================
# EMOJI STICKERS
# =========================

EMOJI_STICKERS = [
    "✨", "💞", "💖", "❣️", "👾", "🌝", "🌞", "🌛", 
    "😺", "🌟", "🔥", "💥", "💢", "💗", "🤍", 
    "💘", "🧡", "💜", "💝", "⭐", "🌙", "☀️", "🌈",
    "🎵", "🎶", "💫", "⚡", "🎯", "🏆", "👑", "💎"
]

TAG_LIMIT = 30

# =========================
# TEST COMMAND
# =========================

@Client.on_message(filters.command("tagtest") & filters.group)
async def tag_test(client: Client, message: Message):
    """Test if plugin is working"""
    await message.reply_text("✅ **Tagall plugin is ALIVE and WORKING!**")

# =========================
# TAGALL COMMAND
# =========================

@Client.on_message(filters.command("tagall") & filters.group)
async def tag_all(client: Client, message: Message):
    """Tag all members with emoji stickers"""
    
    try:
        # Acknowledge command
        await message.reply_text("⏳ **Processing /tagall...**")
        
        # Check if user is admin
        user_status = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user_status.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text("❌ **Only admins can use this command!**")
            return
        
        # Check if bot is admin
        bot_status = await client.get_chat_member(message.chat.id, client.me.id)
        if bot_status.status not in [ChatMemberStatus.ADMINISTRATOR]:
            await message.reply_text("❌ **Bot needs to be admin to tag members!**")
            return
        
        # Get members
        status_msg = await message.reply_text("🔄 **Collecting members...**")
        members = []
        async for member in client.get_chat_members(message.chat.id):
            if not member.user.is_bot:
                members.append(member)
        
        total = len(members)
        if total == 0:
            await status_msg.edit_text("❌ No members found!")
            return
        
        await status_msg.edit_text(f"🎯 **Tagging {total} members...**")
        
        # Create mentions
        mentions = []
        for member in members:
            emoji = random.choice(EMOJI_STICKERS)
            mentions.append(f"[{emoji}](tg://user?id={member.user.id})")
        
        # Send in batches
        for i in range(0, len(mentions), TAG_LIMIT):
            batch = mentions[i:i+TAG_LIMIT]
            await client.send_message(
                message.chat.id,
                "✨ **Member Stickers** ✨\n\n" + " ".join(batch)
            )
            await asyncio.sleep(0.5)
        
        await status_msg.delete()
        await message.reply_text(f"✅ **Successfully tagged {total} members!**")
        
    except Exception as e:
        logger.error(f"Tagall error: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

# =========================
# TAGLIST COMMAND
# =========================

@Client.on_message(filters.command("taglist") & filters.group)
async def tag_list(client: Client, message: Message):
    """Show available emojis"""
    emoji_list = " ".join(EMOJI_STICKERS[:20])
    await message.reply_text(
        f"🎨 **Available Emoji Stickers:**\n\n"
        f"{emoji_list}\n\n"
        f"📌 **Commands:**\n"
        f"• `/tagall` - Tag all members\n"
        f"• `/taglist` - Show emojis\n"
        f"• `/tagtest` - Test plugin"
    )

# =========================
# PRIVATE CHAT HANDLER
# =========================

@Client.on_message(filters.command("tagall") & filters.private)
async def tag_all_private(client: Client, message: Message):
    """Tag all members - Private chat"""
    await message.reply_text(
        "❌ **This command only works in groups!**\n\n"
        "Add me to a group as admin and try again."
    )
