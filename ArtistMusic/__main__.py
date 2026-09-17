import asyncio

from ArtistMusic.command import commands  # noqa: F401  (registers all the handlers)
from ArtistMusic.engine.bot import app, calls, userbot


async def main():
    await app.start()
    await userbot.start()
    await calls.start()
    print("ArtistMusic is up.")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
