import os
import re
import glob
import asyncio
import aiohttp
from dataclasses import replace
from pathlib import Path
from typing import Optional, Union

from pyrogram import enums, types
from py_yt import Playlist, VideosSearch
from Elevenyts import config, logger
from Elevenyts.helpers import Track, utils


class YouTube:
    def __init__(self):
        """Initialize YouTube handler with API configuration."""
        self.base = "https://www.youtube.com/watch?v="  # Base YouTube URL
        self.api_url = config.YOUTUBE_API_URL  # API URL for downloads

        # Regular expression to match YouTube URLs (videos, shorts, playlists)
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )

        # Cache search results to reduce API calls (10 minute TTL)
        self.search_cache = {}  # {"query_video": (result, timestamp)}
        self.cache_time = {}  # Deprecated, using tuple in search_cache instead

        # **PERFORMANCE FIX**: Limit concurrent downloads to prevent bandwidth saturation
        # With 15-20 groups, unlimited concurrent downloads cause 320+ connections
        self._download_semaphore = asyncio.Semaphore(5)  # Max 5 simultaneous downloads
        self._max_video_height = getattr(config, "VIDEO_MAX_HEIGHT", 1080)

    def _locate_download_file(self, video_id: str, video: bool = False) -> Optional[str]:
        """Locate any completed download file for a video id."""
        pattern = f"downloads/{video_id}*"
        candidates = sorted([
            path for path in glob.glob(pattern)
            if not path.endswith((".part", ".ytdl", ".info.json", ".temp"))
        ])

        video_exts = {".mp4", ".mkv", ".webm", ".mov"}
        audio_exts = {".m4a", ".webm", ".opus", ".mp3", ".ogg", ".wav", ".flac"}

        if video:
            for path in candidates:
                if os.path.isdir(path):
                    continue
                if Path(path).suffix.lower() in video_exts:
                    return path
        else:
            for path in candidates:
                if os.path.isdir(path):
                    continue
                if Path(path).suffix.lower() in audio_exts:
                    return path

        for path in candidates:
            if os.path.isdir(path):
                continue
            return path
        return None

    def valid(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL."""
        return bool(re.match(self.regex, url))

    def url(self, message_1: types.Message) -> Union[str, None]:
        """Extract YouTube URL from message."""
        messages = [message_1]
        link = None
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)

        for message in messages:
            text = message.text or message.caption or ""

            if message.entities:
                for entity in message.entities:
                    if entity.type == enums.MessageEntityType.URL:
                        link = text[entity.offset: entity.offset +
                                    entity.length]
                        break

            if message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == enums.MessageEntityType.TEXT_LINK:
                        link = entity.url
                        break

        if link:
            return link.split("&si")[0].split("?si")[0]
        return None

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        """Search for a video on YouTube."""
        # Check cache first (10-minute TTL)
        cache_key = f"{query}_{video}"
        current_time = asyncio.get_running_loop().time()

        if cache_key in self.search_cache:
            cached_result, cache_timestamp = self.search_cache[cache_key]
            if current_time - cache_timestamp < 600:  # 10 minutes
                # Return a fresh copy so downstream mutations don't leak back into cache
                fresh = replace(cached_result)
                fresh.message_id = m_id
                fresh.file_path = None
                fresh.user = None
                fresh.time = 0
                fresh.video = video
                return fresh

        try:
            _search = VideosSearch(query, limit=1)
            results = await _search.next()
        except Exception as e:
            logger.warning(f"⚠️ YouTube search failed for '{query}': {e}")
            return None

        if results and results["result"]:
            data = results["result"][0]
            duration = data.get("duration")
            is_live = duration is None or duration == "LIVE"

            track = Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=duration if not is_live else "LIVE",
                duration_sec=0 if is_live else utils.to_seconds(duration),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get(
                    "thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                is_live=is_live,
                video=video,
            )

            # Cache the result
            self.search_cache[cache_key] = (track, current_time)
            # Limit cache size to 100 entries
            if len(self.search_cache) > 100:
                oldest_key = min(self.search_cache.keys(),
                                 key=lambda k: self.search_cache[k][1])
                del self.search_cache[oldest_key]

            return replace(track)
        return None

    async def playlist(self, limit: int, user: str, url: str) -> list[Track]:
        """Extract playlist tracks."""
        try:
            plist = await Playlist.get(url)
            tracks = []

            # Check if plist has videos
            if not plist or "videos" not in plist or not plist["videos"]:
                return []

            for data in plist["videos"][:limit]:
                try:
                    # Get thumbnail safely
                    thumbnails = data.get("thumbnails", [])
                    thumbnail_url = ""
                    if thumbnails and len(thumbnails) > 0:
                        thumbnail_url = thumbnails[-1].get(
                            "url", "").split("?")[0]

                    # Get link safely
                    link = data.get("link", "")
                    if "&list=" in link:
                        link = link.split("&list=")[0]

                    track = Track(
                        id=data.get("id", ""),
                        channel_name=data.get("channel", {}).get("name", ""),
                        duration=data.get("duration", "0:00"),
                        duration_sec=utils.to_seconds(
                            data.get("duration", "0:00")),
                        title=(data.get("title", "Unknown")[:25]),
                        thumbnail=thumbnail_url,
                        url=link,
                        user=user,
                        view_count="",
                        is_live=False,
                        video=False,
                    )
                    tracks.append(track)
                except Exception as e:
                    # Skip individual track errors
                    continue

            return tracks
        except KeyError as e:
            # Handle YouTube API structure changes
            raise Exception(
                f"Failed to parse playlist. YouTube may have changed their structure.")
        except Exception as e:
            # Re-raise other exceptions
            raise

    async def _download_via_api(self, video_id: str, video: bool = False) -> Optional[str]:
        """
        Download audio/video using external API.
        This replaces the cookie-based yt-dlp approach.
        """
        file_type = "video" if video else "audio"
        ext = "mp4" if video else "mp3"
        file_path = os.path.join("downloads", f"{video_id}.{ext}")

        # Check if file already exists
        if os.path.exists(file_path):
            return file_path

        # Ensure downloads directory exists
        downloads_dir = Path("downloads")
        if not downloads_dir.exists():
            try:
                downloads_dir.mkdir(parents=True, exist_ok=True)
                logger.info("📁 Created downloads directory")
            except Exception as e:
                logger.error(f"❌ Cannot create downloads directory: {e}")
                return None

        try:
            async with aiohttp.ClientSession() as session:
                # First, get download token
                params = {"url": video_id, "type": file_type}
                
                async with session.get(
                    f"{self.api_url}/download",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=7)
                ) as response:
                    if response.status != 200:
                        logger.error(f"❌ API request failed: HTTP {response.status}")
                        return None

                    data = await response.json()
                    download_token = data.get("download_token")
                    
                    if not download_token:
                        logger.error("❌ No download token received from API")
                        return None
                    
                    # Download the file
                    stream_url = f"{self.api_url}/stream/{video_id}?type={file_type}&token={download_token}"
                    
                    async with session.get(
                        stream_url,
                        timeout=aiohttp.ClientTimeout(total=300 if video else 300)
                    ) as file_response:
                        if file_response.status == 302:
                            # Handle redirect
                            redirect_url = file_response.headers.get('Location')
                            if redirect_url:
                                async with session.get(redirect_url) as final_response:
                                    if final_response.status != 200:
                                        logger.error(f"❌ Redirect failed: HTTP {final_response.status}")
                                        return None
                                    with open(file_path, "wb") as f:
                                        async for chunk in final_response.content.iter_chunked(16384):
                                            f.write(chunk)
                        elif file_response.status == 200:
                            # Direct download
                            with open(file_path, "wb") as f:
                                async for chunk in file_response.content.iter_chunked(16384):
                                    f.write(chunk)
                        else:
                            logger.error(f"❌ Download failed: HTTP {file_response.status}")
                            return None
                        
                        # Verify file was downloaded
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                            logger.info(f"✅ Downloaded: {video_id}.{ext}")
                            return file_path
                        else:
                            logger.error(f"❌ Downloaded file is empty or missing: {file_path}")
                            return None

        except asyncio.TimeoutError:
            logger.error(f"❌ Download timeout for {video_id}")
            return None
        except Exception as e:
            logger.error(f"❌ Download error for {video_id}: {e}")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            return None

    async def download(self, video_id: str, is_live: bool = False, video: bool = False) -> Optional[str]:
        """
        Download a video or audio from YouTube using API.
        
        Args:
            video_id: YouTube video ID
            is_live: Whether this is a live stream
            video: True for video download, False for audio only
        
        Returns:
            Path to downloaded file or stream URL for live content
        """
        url = self.base + video_id

        # For live streams, we need to extract the stream URL
        if is_live:
            # Try to get live stream URL via API
            try:
                async with aiohttp.ClientSession() as session:
                    params = {"url": video_id, "type": "live"}
                    async with session.get(
                        f"{self.api_url}/live",
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            stream_url = data.get("stream_url")
                            if stream_url:
                                return stream_url
            except Exception as e:
                logger.warning(f"⚠️ Failed to get live stream URL: {e}")
            
            # Fallback: return the YouTube URL directly (player will handle it)
            return url

        # Use semaphore to limit concurrent downloads
        async with self._download_semaphore:
            return await self._download_via_api(video_id, video)
