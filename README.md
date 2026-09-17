<div align="center">

<img src="https://files.catbox.moe/f4nnyn.svg" width="100%" height="300">

<br><br>

[![License](https://img.shields.io/badge/License-MIT-A960FF?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=0D1117)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-2CA5E0?style=for-the-badge&logo=python&logoColor=white&labelColor=0D1117)](https://www.python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-Client-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white&labelColor=0D1117)](https://docs.pyrogram.org)

</div>

<br>

<div align="center">

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                  ✦  ARTISTMUSIC MUSIC BOT  ✦
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

</div>

## 📖 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Requirements](#-requirements)
- [Environment Variables](#-environment-variables)
- [Setup](#-setup)
- [Commands](#-commands)
- [Notes](#-notes)
- [License](#-license)

<br>

## 〔 ✦ 〕 Overview

> **ArtistMusic** is a lightweight Telegram Voice Chat Music Bot.
> Built on **Pyrogram** · **PyTgCalls** · **MongoDB** — one bot account handles
> commands, and one assistant (userbot) account joins the voice chat and
> streams the audio.

This is a deliberately small, single-file-per-concern build: no queue
database, no multi-language files — just enough to search YouTube, join a
voice chat, and control playback.

<br>

## 〔 ✦ 〕 Features

```
✦ YouTube Search & Direct Link Play      ✦ Pause / Resume
✦ Video-Call Play (vplay)                ✦ Skip / Stop / End
✦ Force Play (skip the queue)            ✦ Seek Forward / Backward
✦ Auto Queue + Auto-Advance              ✦ Restart Current Track
✦ Loop Current Track (0–10 times)        ✦ Inline Player Buttons
✦ Owner Broadcast                        ✦ Ping / Latency Check
```

<br>

## 〔 ✦ 〕 Project Structure

```
ArtistMusic-main/
├── ArtistMusic/
│   ├── __init__.py
│   ├── __main__.py        # entry point — run with: python -m ArtistMusic
│   ├── command/
│   │   ├── __init__.py
│   │   └── commands.py     # play, vplay, playforce, vplayforce, skip, stop,
│   │                        # end, seek, seekback, resume, pause, loop,
│   │                        # restart, ping, broadcast
│   └── engine/
│       ├── __init__.py
│       ├── data.py          # MongoDB — remembers served chats
│       ├── bot.py           # bot client, userbot client, PyTgCalls, inline buttons
│       └── artist.py        # YouTube search/download, broadcast
├── Dockerfile
├── LICENSE
├── README.md
├── config.py
├── requirements.txt
└── sample.env
```

<br>

## 〔 ✦ 〕 Requirements

| Component | Minimum Version / Note |
|:---|:---|
| Python | 3.10 or higher |
| FFmpeg | Latest stable release |
| MongoDB | Local instance or Atlas cluster |
| Telegram Account | For the assistant (string session) |

<br>

## 〔 ✦ 〕 Environment Variables

<div align="center">

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      Create a  .env  file with these values
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

</div>

| Variable | Required | Description |
|:---|:---:|:---|
| `API_ID` | ✅ | From [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | ✅ | From [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | ✅ | From [@BotFather](https://t.me/BotFather) |
| `SESSION_STRING` | ✅ | Pyrogram string session for the assistant account |
| `MONGO_URL` | ✅ | MongoDB connection string |
| `OWNER_ID` | ✅ | Your numeric Telegram user id (needed for `/broadcast`) |
| `DURATION_LIMIT_MIN` | ❌ | Max track length in minutes (default: `60`) |

<br>

## 〔 ✦ 〕 Setup

1. Install dependencies (needs `ffmpeg` installed on the system too):
   ```
   pip install -r requirements.txt
   ```
2. Copy `sample.env` to `.env` and fill in the variables above.
3. Generate a string session for the assistant account and put it in
   `SESSION_STRING`.
4. Add both the bot and the assistant account to your group, and give the
   assistant permission to start/join the voice chat.
5. Run it from the repo root:
   ```
   python -m ArtistMusic
   ```

<br>

## 〔 ✦ 〕 Commands

| Command | Description |
|:---|:---|
| `/play <name\|link>` | Play or queue a song |
| `/vplay <name\|link>` | Play or queue a video |
| `/playforce <name\|link>` | Skip current and play now |
| `/vplayforce <name\|link>` | Skip current and video-play now |
| `/skip` | Play the next track in queue |
| `/pause` | Pause playback |
| `/resume` | Resume playback |
| `/seek <secs>` | Jump forward |
| `/seekback <secs>` | Jump backward |
| `/restart` | Replay current track from 0:00 |
| `/loop <0-10>` | Repeat the current track |
| `/stop` / `/end` | Stop and clear the queue |
| `/ping` | Check bot latency |
| `/broadcast` | Send a message to every served chat (owner only) |

<br>

## 〔 ✦ 〕 Notes

- Queue/loop state is kept in memory per-process — simple on purpose, but it
  resets on restart and won't work across multiple bot instances.
- `py-tgcalls` changes its API a bit between versions. This targets the
  2.x line (`MediaStream`, `AudioQuality`, `calls.play` /
  `calls.change_stream` / `calls.leave_call`). If a call in
  `ArtistMusic/command/commands.py` or `ArtistMusic/engine/bot.py` doesn't
  match what you have installed, check that package's changelog for the
  equivalent call.
- All bot-facing text is written directly inline in
  `ArtistMusic/command/commands.py` — edit the strings there if you want to
  change the wording.

<br>

## 〔 ✦ 〕 License

Released under the [MIT License](LICENSE).
