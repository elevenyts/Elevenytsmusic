# ==========================================================
# Copyright (c) 2026 VelocityBots
# All Rights Reserved.
#
# Project      : VelocityBots ꭙ Music Telegram Bot
# Powered By   : Artist
# Type         : API Based Telegram Music Bot
#
# Bot          : @ArtistApibot
# Channel      : https://t.me/artistbots
# GitHub       : https://github.com/elevenyts
#
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================

import re
import asyncio
from functools import wraps

from pyrogram import filters, types
from pyrogram.errors import FloodWait, QueryIdInvalid

from Elevenyts import tune, app, config, db, lang, logger, queue, tg, yt
from Elevenyts.helpers import admin_check, buttons, can_manage_vc
from Elevenyts.helpers.rich_player import edit_player


def safe_callback(func):
    """Decorator to handle exceptions in callback handlers."""
    @wraps(func)
    async def wrapper(client, query: types.CallbackQuery):
        try:
            return await func(client, query)
        except QueryIdInvalid:
            return
        except Exception as e:
            logger.error(f"Error in callback {func.__name__}: {e}", exc_info=True)
            try:
                await query.answer("❌ An error occurred. Please try again.", show_alert=True)
            except Exception:
                pass
    return wrapper


@app.on_callback_query(filters.regex("^start$") & ~app.bl_users)
@lang.language()
@safe_callback
async def _start_callback(_, query: types.CallbackQuery):
    """Handle start button callback - return to start message."""
    await query.answer()
    
    _text = query.lang["start_pm"].format(query.from_user.first_name, app.name)
    key = buttons.start_key(query.lang, True)
    
    try:
        await query.edit_message_caption(
            caption=_text,
            reply_markup=key,
        )
    except Exception:
        try:
            await query.edit_message_text(
                text=_text,
                reply_markup=key,
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex("cancel_dl") & ~app.bl_users)
@lang.language()
@safe_callback
async def cancel_dl(_, query: types.CallbackQuery):
    await query.answer()
    await tg.cancel(query)


@app.on_callback_query(filters.regex(r"^(controls)(?:\s|$)|^queueplay(?:\||\s)") & ~app.bl_users)
@lang.language()
@safe_callback
async def _controls(_, query: types.CallbackQuery):
    raw = str(query.data or "").strip()
    # Rich queue button format is pipe-delimited, so split the raw callback
    # first.  Do NOT call .split() and then expect args[0] == "queueplay";
    # for data like queueplay|-100123|VIDEO_ID that would be one token.
    args = raw.split()
    if raw.startswith("queueplay"):
        # Rich queue button format: queueplay|<chat_id>|<item_id>
        # Keep a space-delimited fallback for older queue messages.
        if "|" in raw:
            parts = raw.split("|", 2)
            if len(parts) != 3:
                return await query.answer("This queue button is invalid.", show_alert=True)
            _, chat_raw, item_id = parts
            try:
                chat_id = int(chat_raw)
            except ValueError:
                return await query.answer("This queue button is invalid.", show_alert=True)
        else:
            parts = raw.split()
            if len(parts) < 3:
                return await query.answer("This queue button is no longer valid.", show_alert=True)
            try:
                chat_id = int(parts[1])
            except (ValueError, TypeError):
                return await query.answer("This queue button is no longer valid.", show_alert=True)
            item_id = parts[2]

        user_id = query.from_user.id
        has_permission = user_id in app.sudoers or await db.is_auth(chat_id, user_id)
        if not has_permission:
            admins = await db.get_admins(chat_id)
            has_permission = user_id in admins
        if not has_permission:
            return await query.answer("⚠️ You don't have permission to use this.", show_alert=True)

        if not await db.get_call(chat_id):
            return await query.answer(query.lang["not_playing"], show_alert=True)

        # Promote the exact queued item to the immediate next position.
        # play_next() then removes the current item and starts this selected song.
        selected = queue.play_next_item(chat_id, item_id)
        if not selected:
            return await query.answer("This queued song is no longer available.", show_alert=True)

        await query.answer("▶️ Playing now")
        try:
            await query.message.delete()
        except Exception:
            pass

        # force_new_message is important: it removes the old player and the
        # selected queue card, then creates a fresh player for the selected song.
        await tune.play_next(chat_id, force_new_message=True)
        return

    # Guard against stale/legacy Rich buttons with incomplete callback data.
    # Never index args[1]/args[2] until the callback has the expected shape.
    if len(args) < 3:
        await query.answer("This button is no longer valid. Please use the current player.", show_alert=True)
        return

    try:
        action, chat_id = args[1], int(args[2])
    except (ValueError, TypeError):
        await query.answer("This button is no longer valid. Please use the current player.", show_alert=True)
        return

    qaction = len(args) == 4
    user = query.from_user.mention

    # Handle close action first - allow any user to delete the message (no popup notification)
    if action == "close":
        await query.answer()
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    # Check admin permissions for all other controls
    # Inline permission check: sudo users, authorized users, or group admins
    user_id = query.from_user.id
    has_permission = False
    
    if user_id in app.sudoers:
        has_permission = True
    elif await db.is_auth(chat_id, user_id):
        has_permission = True
    else:
        admins = await db.get_admins(chat_id)
        if user_id in admins:
            has_permission = True
    
    if not has_permission:
        return await query.answer("⚠️ You don't have permission to use this.", show_alert=True)

    if not await db.get_call(chat_id):
        return await query.answer(query.lang["not_playing"], show_alert=True)

    if action == "status":
        return await query.answer()

    if action == "auto":
        current_auto = await db.get_autoplay(chat_id)
        new_auto = not current_auto
        await db.set_autoplay(chat_id, new_auto)
        state_text = "Autoplay ON — next song will start automatically." if new_auto else "Autoplay OFF."
        await query.answer(state_text, show_alert=True)
        current = queue.get_current(chat_id)
        if current and query.message:
            try:
                base = query.lang["play_media"].format(
                    current.url, current.title, current.duration, current.user
                )
                await edit_player(
                    chat_id, query.message.id, base, current,
                    playing=not await db.playing(chat_id),
                )
            except Exception as e:
                logger.debug(f"Could not refresh player after autoplay toggle for {chat_id}: {e}")
        return

    if action == "queue":
        items = queue.get_queue(chat_id)
        if not items or len(items) <= 1:
            return await query.answer("🎵 Queue is empty.", show_alert=True)
        lines = ["🎵 <b>UP NEXT</b>"]
        for index, item in enumerate(items[1:11], 1):
            lines.append(f"<b>{index}.</b> {item.title}")
        return await query.answer("\n".join(lines), show_alert=True)
    
    # Handle seek actions
    if action.startswith("seek_"):
        return await handle_seek(query, chat_id, action, user)
    
    # Handle loop action
    if action == "loop":
        return await handle_loop(query, chat_id, user)
    
    # Handle shuffle action
    if action == "shuffle":
        return await handle_shuffle(query, chat_id, user)
    
    await query.answer(query.lang["processing"], show_alert=True)

    if action == "pause":
        if not await db.playing(chat_id):
            return await query.answer(
                query.lang["play_already_paused"], show_alert=True
            )
        if not await tune.pause(chat_id):
            return await query.answer(query.lang["not_playing"], show_alert=True)
        current = queue.get_current(chat_id)
        if current:
            current._clock_last = asyncio.get_running_loop().time()
        status = query.lang["paused"]
        reply = query.lang["play_paused"].format(user)

    elif action == "resume":
        status = query.lang["playing"]
        if await db.playing(chat_id):
            return await query.answer(query.lang["play_not_paused"], show_alert=True)
        if not await tune.resume(chat_id):
            return await query.answer(query.lang["not_playing"], show_alert=True)
        current = queue.get_current(chat_id)
        if current:
            current._clock_last = asyncio.get_running_loop().time()
        reply = query.lang["play_resumed"].format(user)

    elif action == "skip":
        await tune.play_next(chat_id, force_new_message=True)
        await query.answer(query.lang["skipped"])
        return

    elif action == "force":
        pos, media = queue.check_item(chat_id, args[3])
        if not media or pos == -1:
            return await query.edit_message_text(query.lang["play_expired"])

        current = queue.get_current(chat_id)
        m_id = current.message_id if current else None
        queue.force_add(chat_id, media, remove=pos)
        try:
            await app.delete_messages(
                chat_id=chat_id, message_ids=[
                    m_id, media.message_id], revoke=True
            )
            media.message_id = None
        except:
            pass

        msg = await app.send_message(chat_id=chat_id, text=query.lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(
                media.id,
                video=getattr(media, "video", False),
            )
        media.message_id = msg.id
        return await tune.play_media(chat_id, msg, media)

    elif action == "replay":
        media = queue.get_current(chat_id)
        if not media:
            return await query.answer(query.lang["not_playing"], show_alert=True)
        media.user = user
        await tune.replay(chat_id, control_message=query.message)
        await query.answer(query.lang["replayed"])
        return

    elif action == "stop":
        await tune.stop(chat_id)
        status = query.lang["stopped"]
        reply = query.lang["play_stopped"].format(user)

    try:
        if action in ["pause", "resume"]:
            current = queue.get_current(chat_id)
            if current and query.message:
                base = query.lang["play_media"].format(
                    current.url, current.title, current.duration, current.user
                )
                ok = await edit_player(
                    chat_id, query.message.id, base, current,
                    playing=(action == "resume"),
                )
                if ok:
                    return
            # If this wasn't a Rich Message, retain the original inline behavior.
            mtext = re.sub(
                r"\n\n<blockquote>.*?</blockquote>", "",
                getattr(query.message.caption, "html", None) or getattr(query.message.text, "html", ""),
                flags=re.DOTALL,
            )
            keyboard = buttons.controls(chat_id, status=status if action != "resume" else None)
        elif action in ["skip", "replay", "stop"]:
            sent_msg = None
            try:
                sent_msg = await query.message.reply_text(reply, quote=False)
            except FloodWait as e:
                # If FloodWait occurs, wait and retry once
                await asyncio.sleep(e.value)
                try:
                    sent_msg = await query.message.reply_text(reply, quote=False)
                except Exception:
                    pass
            except Exception:
                pass
            # Keep the Rich player alive during playback controls. Deleting it
            # also removes the attached thumbnail.
            if action not in {"skip", "replay", "stop"}:
                try:
                    await query.message.delete()
                except Exception:
                    pass
            
            # Auto-delete the reply message after 5 seconds
            if sent_msg:
                await asyncio.sleep(5)
                try:
                    await sent_msg.delete()
                except Exception:
                    pass
        else:
            mtext = re.sub(
                r"\n\n<blockquote>.*?</blockquote>",
                "",
                query.message.caption.html or query.message.text.html,
                flags=re.DOTALL,
            )
            keyboard = buttons.controls(
                chat_id, status=status if action != "resume" else None
            )
        await query.edit_message_text(
            f"{mtext}\n\n<blockquote>{reply}</blockquote>", reply_markup=keyboard
        )
    except FloodWait as e:
        # Handle FloodWait on edit_message_text
        await asyncio.sleep(e.value)
        try:
            await query.edit_message_text(
                f"{mtext}\n\n<blockquote>{reply}</blockquote>", reply_markup=keyboard
            )
        except Exception:
            pass
    except Exception:
        pass


async def handle_seek(query: types.CallbackQuery, chat_id: int, action: str, user: str):
    """Handle seek forward/backward actions."""
    media = queue.get_current(chat_id)
    if not media or media.is_live:
        return await query.answer("⚠️ Cannot seek in live streams!", show_alert=True)
    
    if not media.duration_sec or media.duration_sec == 0:
        return await query.answer("⚠️ Cannot seek in this track!", show_alert=True)
    
    # Determine seek amount and direction
    if action == "seek_back_10":
        seconds = -10
        label = "« 10s"
    elif action == "seek_back_30":
        seconds = -30
        label = "« 30s"
    elif action == "seek_forward_10":
        seconds = 10
        label = "10s »"
    elif action == "seek_forward_30":
        seconds = 30
        label = "30s »"
    else:
        return await query.answer("⚠️ Invalid seek action!", show_alert=True)
    
    # Calculate new position
    current_time = getattr(media, 'time', 0)
    new_time = max(0, min(current_time + seconds, media.duration_sec - 5))
    
    # Check if we're at the boundaries
    if new_time == 0 and seconds < 0:
        return await query.answer(f"⏮️ Already at the beginning!", show_alert=True)
    if new_time >= media.duration_sec - 5 and seconds > 0:
        return await query.answer(f"⏭️ Too close to the end!", show_alert=True)
    
    # Perform seek
    success = await tune.seek_stream(chat_id, int(new_time))
    if success:
        media._clock_last = asyncio.get_running_loop().time()
        # Format time display
        import time as time_module
        if media.duration_sec >= 3600:
            time_str = time_module.strftime('%H:%M:%S', time_module.gmtime(new_time))
        else:
            time_str = time_module.strftime('%M:%S', time_module.gmtime(new_time))
        
        # Use callback answer to avoid FloodWait
        _dir = "⏩ ꜰᴏʀᴡᴀʀᴅᴇᴅ" if seconds > 0 else "⏪ ʀᴇᴡɪɴᴅᴇᴅ"
        await query.answer(f"Seeked to {time_str}", show_alert=True)
        
        # Try to send reply message with FloodWait handling and auto-delete after 5 seconds
        try:
            sent_msg = await query.message.reply_text(
                f"<blockquote><b>{_dir}</b>\n\n⏱  ᴅᴜʀᴀᴛɪᴏɴ ╌ {time_str}\n👤  ʙʏ ╌ {user}</blockquote>",
                quote=False
            )
            # Auto-delete after 5 seconds
            await asyncio.sleep(5)
            try:
                await sent_msg.delete()
            except Exception:
                pass
        except FloodWait as e:
            # If rate limited, just skip the message since user already got feedback via callback
            pass
        except Exception:
            pass


async def handle_loop(query: types.CallbackQuery, chat_id: int, user: str):
    """Handle loop mode toggling."""
    current_loop = await db.get_loop(chat_id)
    
    # Cycle through loop modes: 0 (off) -> 1 (single) -> 10 (queue) -> 0
    if current_loop == 0:
        new_loop = 1
        text = "🔂 Loop: Single Track"
        message = f"🔂 Loop mode set to <b>Single Track</b>"
    elif current_loop == 1:
        new_loop = 10
        text = "🔁 Loop: Queue"
        message = f"🔁 Loop mode set to <b>Queue</b>"
    else:
        new_loop = 0
        text = "➡️ Loop: Off"
        message = f"➡️ Loop mode <b>Disabled</b>"
    
    await db.set_loop(chat_id, new_loop)
    await query.answer(text, show_alert=False)
    await query.message.reply_text(message, quote=False)


async def handle_shuffle(query: types.CallbackQuery, chat_id: int, user: str):
    """Handle queue shuffling."""
    import random
    
    items = queue.get_queue(chat_id)
    if not items or len(items) <= 1:
        return await query.answer("⚠️ Queue is empty or has only one track!", show_alert=True)
    
    # Get current track and remove from list
    current = items[0] if items else None
    remaining = items[1:] if len(items) > 1 else []
    
    if not remaining:
        return await query.answer("⚠️ No tracks to shuffle!", show_alert=True)
    
    # Shuffle remaining tracks
    random.shuffle(remaining)
    
    # Rebuild queue with current track first
    queue.clear(chat_id)
    if current:
        queue.add(chat_id, current)
    for item in remaining:
        queue.add(chat_id, item)
    
    await query.answer("🔀 Queue shuffled!", show_alert=False)
    await query.message.reply_text(
        f"🔀 Queue <b>shuffled</b> ({len(remaining)} tracks)",
        quote=False
    )



@app.on_callback_query(filters.regex(r"^help") & ~app.bl_users)
@lang.language()
async def _help(_, query: types.CallbackQuery):
    await query.answer()
    
    # Handle plain "help" callback - show main menu
    if query.data == "help":
        try:
            # Try to edit as photo message first
            await query.edit_message_caption(
                caption=query.lang["help_menu"], 
                reply_markup=buttons.help_markup(query.lang)
            )
        except Exception:
            # Fallback to text edit if not a photo message
            try:
                await query.edit_message_text(
                    text=query.lang["help_menu"], 
                    reply_markup=buttons.help_markup(query.lang)
                )
            except Exception:
                pass
        return
    
    category = query.data.replace("help_", "")
    
    if category == "main":
        # Return to main help menu from category
        try:
            await query.edit_message_caption(
                caption=query.lang["help_menu"], 
                reply_markup=buttons.help_markup(query.lang)
            )
        except Exception:
            try:
                await query.edit_message_text(
                    text=query.lang["help_menu"], 
                    reply_markup=buttons.help_markup(query.lang)
                )
            except Exception:
                pass
        return

    if category == "langs":
        try:
            await query.edit_message_caption(
                caption=query.lang["lang_select"],
                reply_markup=buttons.langs_markup(),
            )
        except Exception:
            try:
                await query.edit_message_text(
                    text=query.lang["lang_select"],
                    reply_markup=buttons.langs_markup(),
                )
            except Exception:
                pass
        return

    # Handle all help categories
    help_texts = {
        "admins": query.lang["help_admins"],
        "auth": query.lang["help_auth"],
        "broadcast": query.lang["help_sudo"],  # Broadcast is sudo feature
        "blchat": query.lang["help_blchat"],
        "bluser": query.lang["help_bluser"],
        "gban": query.lang["help_gban"],
        "loop": query.lang["help_loop"],
        "play": query.lang["help_play"],
        "queue": query.lang["help_queue"],
        "seek": query.lang["help_seek"],
        "shuffle": query.lang["help_shuffle"],
        "ping": query.lang["help_ping"],
        "stats": query.lang["help_stats"],
        "sudo": query.lang["help_sudo"],
        "maintenance": query.lang["help_maintenance"],
    }
    
    help_text = help_texts.get(category, query.lang["help_admins"])
    
    try:
        await query.edit_message_caption(
            caption=help_text,
            reply_markup=buttons.help_markup(query.lang, True),
        )
    except Exception:
        try:
            await query.edit_message_text(
                text=help_text,
                reply_markup=buttons.help_markup(query.lang, True),
            )
        except Exception:
            pass


_LANG_NAMES = {
    "en": "🇬🇧 English", "hi": "🇮🇳 Hindi", "te": "🇮🇳 Telugu",
    "ko": "🇰🇷 Korean", "my": "🇲🇲 Myanmar", "id": "🇮🇩 Indonesian",
    "pt": "🇧🇷 Portuguese", "ar": "🇸🇦 Arabic", "es": "🇪🇸 Spanish",
    "fr": "🇫🇷 French", "ru": "🇷🇺 Russian", "de": "🇩🇪 German",
    "tr": "🇹🇷 Turkish", "bn": "🇧🇩 Bengali", "th": "🇹🇭 Thai",
    "vi": "🇻🇳 Vietnamese", "ja": "🇯🇵 Japanese", "zh": "🇨🇳 Chinese",
    "ur": "🇵🇰 Urdu", "fa": "🇮🇷 Persian",
}


@app.on_callback_query(filters.regex(r"^setlang_") & ~app.bl_users)
async def _setlang(_, query: types.CallbackQuery):
    code = query.data.replace("setlang_", "")
    if code not in _LANG_NAMES:
        return await query.answer("❌ Invalid language.", show_alert=True)
    lang_name = _LANG_NAMES[code]
    await db.set_lang(query.from_user.id, code)
    new_lang = lang.get_merged_lang(code)
    confirmation = new_lang["lang_changed"].format(lang_name)
    await query.answer()
    try:
        await query.edit_message_caption(
            caption=confirmation,
            reply_markup=buttons.langs_markup(),
        )
    except Exception:
        try:
            await query.edit_message_text(
                text=confirmation,
                reply_markup=buttons.langs_markup(),
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex("^playmode$") & ~app.bl_users)
@lang.language()
@admin_check
async def _playmode(_, query: types.CallbackQuery):
    await query.answer(query.lang["processing"], show_alert=True)
    chat_id = query.message.chat.id
    admin_only = await db.get_play_mode(chat_id)
    force_admin = await db.get_force_mode(chat_id)
    _language = "en"
    await db.set_play_mode(chat_id, admin_only)
    await query.edit_message_reply_markup(
        reply_markup=buttons.settings_markup(
            query.lang,
            not admin_only,
            force_admin,
            _language,
            chat_id,
        )
    )


@app.on_callback_query(filters.regex("^forcemode$") & ~app.bl_users)
@lang.language()
@admin_check
async def _forcemode(_, query: types.CallbackQuery):
    await query.answer(query.lang["processing"], show_alert=True)
    chat_id = query.message.chat.id
    admin_only = await db.get_play_mode(chat_id)
    force_admin = await db.get_force_mode(chat_id)
    _language = "en"
    await db.set_force_mode(chat_id, force_admin)
    await query.edit_message_reply_markup(
        reply_markup=buttons.settings_markup(
            query.lang,
            admin_only,
            not force_admin,
            _language,
            chat_id,
        )
    )
