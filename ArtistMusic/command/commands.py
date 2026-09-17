# NOTE: pytgcalls' exact API (MediaStream / AudioQuality / VideoQuality /
# StreamEnded / calls.play / calls.change_stream ...) can shift slightly
# between minor versions. This file targets py-tgcalls 2.x. If a call
# doesn't match your installed version, check that package's docs/changelog.

import time

from pyrogram import filters
from pyrogram.types import CallbackQuery, Message
from pytgcalls.types import AudioQuality, MediaStream, Update, VideoQuality
from pytgcalls.types.stream import StreamEnded

import config
from ArtistMusic.engine import artist
from ArtistMusic.engine.bot import app, calls, player_buttons
from ArtistMusic.engine.data import add_served_chat

# In-memory state: chat_id -> [...]. Fine for a single-process simple bot.
QUEUES: dict = {}
CURRENT: dict = {}
LOOPS: dict = {}


def _stream(file: str, video: bool, seek_seconds: int = 0) -> MediaStream:
    return MediaStream(
        file,
        audio_parameters=AudioQuality.STUDIO,
        video_parameters=VideoQuality.SD_480p if video else None,
        ffmpeg_parameters=f"-ss {seek_seconds}" if seek_seconds else None,
    )


async def _join_and_play(chat_id: int, track: dict, video: bool) -> None:
    await calls.play(chat_id, _stream(track["file"], video))
    CURRENT[chat_id] = {**track, "video": video, "started": time.time(), "offset": 0}


async def _change_to(chat_id: int, track: dict, video: bool, seek_seconds: int = 0) -> None:
    await calls.change_stream(chat_id, _stream(track["file"], video, seek_seconds))
    CURRENT[chat_id] = {**track, "video": video, "started": time.time(), "offset": seek_seconds}


async def _leave(chat_id: int) -> None:
    try:
        await calls.leave_call(chat_id)
    except Exception:
        pass


async def play_next(chat_id: int) -> dict | None:
    """Advance to the next queued track, or leave the call if empty."""
    queue = QUEUES.get(chat_id, [])
    if queue:
        track = queue.pop(0)
        await _change_to(chat_id, track, track.get("video", False))
        return track
    await _leave(chat_id)
    CURRENT.pop(chat_id, None)
    return None


def _elapsed(chat_id: int) -> int:
    track = CURRENT.get(chat_id)
    if not track:
        return 0
    return int(track["offset"] + (time.time() - track["started"]))


async def _seek_to(chat_id: int, position: int) -> None:
    track = CURRENT[chat_id]
    position = max(0, position)
    await _change_to(chat_id, track, track.get("video", False), seek_seconds=position)


# ---------------------------------------------------------------- basics

@app.on_message(filters.command(["start"]))
async def start_cmd(client, message: Message):
    mention = message.from_user.mention if message.from_user else "there"
    await message.reply_text(
        f"Hi {mention}! I'm a simple music bot for group voice chats.\n"
        "Use /play <song name or link> to start."
    )


@app.on_message(filters.command(["help"]))
async def help_cmd(client, message: Message):
    await message.reply_text(
        "**Commands**\n"
        "/play <name|link> - play or queue a song\n"
        "/vplay <name|link> - play or queue a video\n"
        "/playforce <name|link> - skip current and play now\n"
        "/vplayforce <name|link> - skip current and video-play now\n"
        "/skip - play the next track in queue\n"
        "/pause - pause playback\n"
        "/resume - resume playback\n"
        "/seek <secs> - jump forward\n"
        "/seekback <secs> - jump backward\n"
        "/restart - replay current track from 0:00\n"
        "/loop <0-10> - repeat current track\n"
        "/stop or /end - stop and clear the queue\n"
        "/ping - check bot latency"
    )


@app.on_message(filters.command(["ping"]))
async def ping_cmd(client, message: Message):
    start = time.time()
    sent = await message.reply_text("Pinging...")
    ms = round((time.time() - start) * 1000, 2)
    await sent.edit_text(f"🏓 Pong! {ms} ms")


# ---------------------------------------------------------------- playback

async def _play(message: Message, video: bool, force: bool) -> None:
    query = " ".join(message.command[1:]) if len(message.command) > 1 else None
    if not query and message.reply_to_message and message.reply_to_message.text:
        query = message.reply_to_message.text
    if not query:
        return await message.reply_text("Give a song name or link, e.g. /play faded alan walker")

    chat_id = message.chat.id
    add_served_chat(chat_id)

    status = await message.reply_text(f"🔎 Searching for **{query}**...")
    info = await artist.get_info(query)
    if not info:
        return await status.edit_text(f"No results found for **{query}**.")

    if config.DURATION_LIMIT and info["duration_seconds"] > config.DURATION_LIMIT:
        limit_min = config.DURATION_LIMIT // 60
        return await status.edit_text(
            f"That track is longer than the {limit_min} minute limit set for this bot."
        )

    file = await artist.download(info["id"], video=video)
    if not file:
        return await status.edit_text("Could not download that track, please try another one.")

    requester = message.from_user.mention if message.from_user else "someone"
    track = {**info, "file": file, "requested_by": requester}

    already_playing = chat_id in CURRENT
    if force and already_playing:
        await _change_to(chat_id, track, video)
        await status.edit_text(
            f"🎶 **Now playing:** {track['title']}\nRequested by: {requester}",
            reply_markup=player_buttons(),
        )
    elif already_playing:
        QUEUES.setdefault(chat_id, []).append(track)
        position = len(QUEUES[chat_id])
        await status.edit_text(
            f"➕ **Queued (#{position}):** {track['title']}\nRequested by: {requester}"
        )
    else:
        await _join_and_play(chat_id, track, video)
        QUEUES.setdefault(chat_id, [])
        await status.edit_text(
            f"🎶 **Now playing:** {track['title']}\nRequested by: {requester}",
            reply_markup=player_buttons(),
        )


@app.on_message(filters.command(["play"]) & filters.group)
async def play_cmd(client, message: Message):
    await _play(message, video=False, force=False)


@app.on_message(filters.command(["vplay"]) & filters.group)
async def vplay_cmd(client, message: Message):
    await _play(message, video=True, force=False)


@app.on_message(filters.command(["playforce"]) & filters.group)
async def playforce_cmd(client, message: Message):
    await _play(message, video=False, force=True)


@app.on_message(filters.command(["vplayforce"]) & filters.group)
async def vplayforce_cmd(client, message: Message):
    await _play(message, video=True, force=True)


@app.on_message(filters.command(["skip"]) & filters.group)
async def skip_cmd(client, message: Message):
    chat_id = message.chat.id
    if chat_id not in CURRENT:
        return await message.reply_text("Nothing is playing right now.")
    LOOPS.pop(chat_id, None)
    next_track = await play_next(chat_id)
    if next_track:
        await message.reply_text(f"⏭ Skipped. Now playing: {next_track['title']}")
    else:
        await message.reply_text("⏭ Skipped. Queue is empty, leaving the voice chat.")


@app.on_message(filters.command(["stop", "end"]) & filters.group)
async def stop_cmd(client, message: Message):
    chat_id = message.chat.id
    QUEUES.pop(chat_id, None)
    CURRENT.pop(chat_id, None)
    LOOPS.pop(chat_id, None)
    await _leave(chat_id)
    await message.reply_text("⏹ Stopped and cleared the queue.")


@app.on_message(filters.command(["pause"]) & filters.group)
async def pause_cmd(client, message: Message):
    chat_id = message.chat.id
    if chat_id not in CURRENT:
        return await message.reply_text("Nothing is playing right now.")
    await calls.pause(chat_id)
    await message.reply_text("⏸ Paused.")


@app.on_message(filters.command(["resume"]) & filters.group)
async def resume_cmd(client, message: Message):
    chat_id = message.chat.id
    if chat_id not in CURRENT:
        return await message.reply_text("Nothing is playing right now.")
    await calls.resume(chat_id)
    await message.reply_text("▶️ Resumed.")


@app.on_message(filters.command(["seek"]) & filters.group)
async def seek_cmd(client, message: Message):
    chat_id = message.chat.id
    if chat_id not in CURRENT:
        return await message.reply_text("Nothing is playing right now.")
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text("Please give the number of seconds to seek, e.g. /seek 20")
    new_pos = _elapsed(chat_id) + int(message.command[1])
    await _seek_to(chat_id, new_pos)
    await message.reply_text(f"⏩ Seeked to {new_pos}s.")


@app.on_message(filters.command(["seekback"]) & filters.group)
async def seekback_cmd(client, message: Message):
    chat_id = message.chat.id
    if chat_id not in CURRENT:
        return await message.reply_text("Nothing is playing right now.")
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text("Please give the number of seconds to seek, e.g. /seekback 20")
    new_pos = max(0, _elapsed(chat_id) - int(message.command[1]))
    await _seek_to(chat_id, new_pos)
    await message.reply_text(f"⏪ Seeked back to {new_pos}s.")


@app.on_message(filters.command(["restart"]) & filters.group)
async def restart_cmd(client, message: Message):
    chat_id = message.chat.id
    if chat_id not in CURRENT:
        return await message.reply_text("Nothing is playing right now.")
    await _seek_to(chat_id, 0)
    await message.reply_text("🔁 Restarted the current track from 0:00.")


@app.on_message(filters.command(["loop"]) & filters.group)
async def loop_cmd(client, message: Message):
    chat_id = message.chat.id
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text("Please give a number between 0 and 10, e.g. /loop 3")
    count = int(message.command[1])
    if not 0 <= count <= 10:
        return await message.reply_text("Please give a number between 0 and 10, e.g. /loop 3")
    if count == 0:
        LOOPS.pop(chat_id, None)
        await message.reply_text("🔁 Looping disabled.")
    else:
        LOOPS[chat_id] = count
        await message.reply_text(f"🔁 Looping the current track {count} time(s).")


# ---------------------------------------------------------------- admin

@app.on_message(filters.command(["broadcast"]) & filters.user(config.OWNER_ID))
async def broadcast_cmd(client, message: Message):
    text = None
    if message.reply_to_message:
        text = message.reply_to_message.text
    elif len(message.command) > 1:
        text = message.text.split(None, 1)[1]
    if not text:
        return await message.reply_text(
            "Reply to a message or give text to broadcast, e.g. /broadcast Hello everyone"
        )
    sent, failed = await artist.broadcast(app, text)
    await message.reply_text(f"✅ Broadcast sent to {sent} chats, failed for {failed} chats.")


# ---------------------------------------------------------------- buttons

@app.on_callback_query(filters.regex("^cb_"))
async def player_buttons_cb(client, query: CallbackQuery):
    chat_id = query.message.chat.id
    action = query.data.split("_", 1)[1]

    if action != "stop" and chat_id not in CURRENT:
        return await query.answer("Nothing is playing right now.", show_alert=True)

    if action == "pause":
        await calls.pause(chat_id)
        await query.answer("Paused")
    elif action == "resume":
        await calls.resume(chat_id)
        await query.answer("Resumed")
    elif action == "skip":
        LOOPS.pop(chat_id, None)
        next_track = await play_next(chat_id)
        await query.answer("Skipped" if next_track else "Queue empty, left the chat")
    elif action == "stop":
        QUEUES.pop(chat_id, None)
        CURRENT.pop(chat_id, None)
        LOOPS.pop(chat_id, None)
        await _leave(chat_id)
        await query.answer("Stopped")


# ---------------------------------------------------------------- auto-advance

@calls.on_update()
async def on_stream_end(_client, update: Update):
    if not isinstance(update, StreamEnded):
        return
    chat_id = update.chat_id

    if LOOPS.get(chat_id, 0) > 0 and chat_id in CURRENT:
        LOOPS[chat_id] -= 1
        await _seek_to(chat_id, 0)
        return

    await play_next(chat_id)
