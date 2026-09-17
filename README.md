# ArtistMusic

A small Telegram voice-chat music bot. It's a stripped-down version of the
usual "userbot music bot" pattern: one bot account for commands, one
assistant (userbot) account that actually joins the voice chat, and
PyTgCalls in between.

```
ArtistMusic-main/
├── ArtistMusic/
│   ├── __init__.py
│   ├── __main__.py     # entry point — run with: python -m ArtistMusic
│   ├── command/
│   │   ├── __init__.py
│   │   └── commands.py   # play, vplay, playforce, vplayforce, skip, stop,
│   │                      # end, seek, seekback, resume, pause, loop,
│   │                      # restart, ping, broadcast
│   └── engine/
│       ├── __init__.py
│       ├── data.py        # MongoDB — remembers served chats
│       ├── bot.py         # bot client, userbot client, PyTgCalls, inline buttons
│       └── artist.py      # YouTube search/download, broadcast
├── Dockerfile
├── LICENSE
├── README.md
├── config.py
├── requirements.txt
└── sample.env
```

## Setup

1. `pip install -r requirements.txt` (needs `ffmpeg` installed on the system too).
2. Copy `sample.env` to `.env` and fill in:
   - `API_ID` / `API_HASH` — from https://my.telegram.org
   - `BOT_TOKEN` — from @BotFather
   - `SESSION_STRING` — a Pyrogram string session for the assistant account
     that will join voice chats (generate one with a small script using
     `pyrogram.Client(...).export_session_string()`)
   - `MONGO_URL` — a MongoDB connection string
   - `OWNER_ID` — your numeric Telegram user id (needed for `/broadcast`)
3. Add both the bot and the assistant account to your group, and give the
   assistant permission to start/join the voice chat.
4. From the repo root: `python -m ArtistMusic`

## Commands

`/play`, `/vplay`, `/playforce`, `/vplayforce`, `/skip`, `/pause`,
`/resume`, `/seek <secs>`, `/seekback <secs>`, `/restart`,
`/loop <0-10>`, `/stop` / `/end`, `/ping`, `/broadcast` (owner only).

## Notes

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
