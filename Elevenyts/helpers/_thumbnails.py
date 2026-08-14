# Copyright (c) 2025 AnonymousX1025
# Modified for EXACT YouTube Music Style Thumbnails
# Like real YouTube Music video thumbnails

import os
import asyncio
import aiohttp
from PIL import (
    Image, ImageDraw, ImageEnhance,
    ImageFilter, ImageFont, ImageOps
)


# =========================
# CONFIGURATION
# =========================

W, H = 1280, 720
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
YELLOW = (255, 200, 0)


# =========================
# HELPER FUNCTIONS
# =========================

def safe_text(text, fallback="Unknown"):
    return text if text else fallback

def fit_text(font, text, max_width):
    """Truncate text with ellipsis if too long"""
    try:
        if font.getlength(text) <= max_width:
            return text
        for i in range(len(text), 0, -1):
            if font.getlength(text[:i] + "…") <= max_width:
                return text[:i] + "…"
        return "…"
    except:
        return text[:50] + "…" if len(text) > 50 else text

def format_views(views):
    """Format view count to K/M format"""
    try:
        views = int(views)
        if views >= 1_000_000:
            return f"{views//1_000_000}M"
        elif views >= 1_000:
            return f"{views//1_000}K"
        return str(views)
    except:
        return "0"

def create_gradient(width, height, color1, color2):
    """Create a vertical gradient"""
    gradient = Image.new('RGBA', (width, height), color1)
    draw = ImageDraw.Draw(gradient)
    for y in range(height):
        ratio = y / height
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        a = int(color1[3] * (1 - ratio) + color2[3] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, a))
    return gradient


# =========================
# TRACK CLASS
# =========================

class Track:
    def __init__(self, id, title, thumbnail, channel_name, view_count, duration):
        self.id = id
        self.title = title
        self.thumbnail = thumbnail
        self.channel_name = channel_name
        self.view_count = view_count
        self.duration = duration


# =========================
# MAIN THUMBNAIL CLASS
# =========================

class Thumbnail:
    """
    EXACT YouTube Music Style Thumbnail Generator
    Like real YouTube Music video thumbnails
    """

    def __init__(self):
        self.session = None
        
        # Load fonts
        try:
            self.font_title = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 65
            )
            self.font_artist = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 32
            )
            self.font_views = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 26
            )
            self.font_sub = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 22
            )
        except:
            print("⚠️ Custom fonts not found, using default")
            self.font_title = ImageFont.load_default()
            self.font_artist = ImageFont.load_default()
            self.font_views = ImageFont.load_default()
            self.font_sub = ImageFont.load_default()

    async def start(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    async def save_thumb(self, output_path, url):
        if not self.session:
            await self.start()
        async with self.session.get(url) as resp:
            with open(output_path, "wb") as f:
                f.write(await resp.read())
        return output_path

    # ========================================
    # YOUTUBE MUSIC STYLE GENERATE
    # ========================================

    async def generate(self, song) -> str:
        """Generate YouTube Music-style thumbnail"""
        try:
            output = f"{CACHE_DIR}/{song.id}_youtube_music.png"
            if os.path.exists(output):
                return output

            temp = f"{CACHE_DIR}/temp_{song.id}.jpg"
            
            url = getattr(song, "thumbnail", None)
            if not url:
                url = f"https://img.youtube.com/vi/{song.id}/maxresdefault.jpg"

            await self.save_thumb(temp, url)

            return await asyncio.get_event_loop().run_in_executor(
                None, self._render_youtube_music, temp, output, song
            )

        except Exception as e:
            print(f"❌ Thumbnail error: {e}")
            return None

    # ========================================
    # YOUTUBE MUSIC RENDER ENGINE
    # ========================================

    def _render_youtube_music(self, temp, output, song):
        """Render exact YouTube Music-style thumbnail"""
        try:
            # Load main image
            img = Image.open(temp).convert("RGBA").resize((W, H))

            # ====== STEP 1: BLUR BACKGROUND ======
            bg_blur = img.copy().filter(ImageFilter.GaussianBlur(35))
            bg_blur = ImageEnhance.Brightness(bg_blur).enhance(0.30)
            bg_blur = ImageEnhance.Contrast(bg_blur).enhance(1.3)

            # ====== STEP 2: DARK OVERLAY ======
            dark = Image.new("RGBA", (W, H), (0, 0, 0, 180))
            bg = Image.alpha_composite(bg_blur, dark)

            # ====== STEP 3: MAIN IMAGE (CENTER - LARGE) ======
            main_img = img.copy()
            
            # Calculate size - keep aspect ratio, fill most of the frame
            target_width = 900
            target_height = int(main_img.height * (target_width / main_img.width))
            
            # If height is too much, adjust
            if target_height > 650:
                target_height = 650
                target_width = int(main_img.width * (target_height / main_img.height))
            
            main_img = main_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Center position
            x_pos = (W - target_width) // 2
            y_pos = (H - target_height) // 2 - 30  # Slightly up for text

            # PASTE WITH NO ROUNDED CORNERS - NO BORDER
            bg.paste(main_img, (x_pos, y_pos), main_img)

            # ====== STEP 4: BOTTOM GRADIENT FOR TEXT ======
            gradient = create_gradient(
                W, 280,
                (0, 0, 0, 0),
                (0, 0, 0, 220)
            )
            bg.paste(gradient, (0, H - 280), gradient)

            draw = ImageDraw.Draw(bg)

            # ====== STEP 5: SONG TITLE (Bold, Large) ======
            title = safe_text(getattr(song, "title", "Unknown Track"))
            title = fit_text(self.font_title, title, 1100)

            title_x = 60
            title_y = H - 160

            # Outline for readability
            for dx, dy in [(-3, -3), (-3, 3), (3, -3), (3, 3)]:
                draw.text(
                    (title_x + dx, title_y + dy),
                    title,
                    font=self.font_title,
                    fill=(0, 0, 0)
                )
            
            # Main white text
            draw.text(
                (title_x, title_y),
                title,
                font=self.font_title,
                fill=WHITE
            )

            # ====== STEP 6: ARTIST NAME ======
            artist = safe_text(getattr(song, "channel_name", "Unknown Artist"))
            artist = fit_text(self.font_artist, artist, 800)
            
            artist_x = title_x
            artist_y = title_y + 75

            # Outline
            for dx, dy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                draw.text(
                    (artist_x + dx, artist_y + dy),
                    artist,
                    font=self.font_artist,
                    fill=(0, 0, 0)
                )
            
            # Artist name in gray
            draw.text(
                (artist_x, artist_y),
                artist,
                font=self.font_artist,
                fill=LIGHT_GRAY
            )

            # ====== STEP 7: VIEWS & DURATION ======
            views = format_views(getattr(song, "view_count", 0))
            duration = safe_text(getattr(song, "duration", "0:00"))
            
            # Duration badge (like YouTube Music)
            badge_text = f"▶ {views} views"
            
            # Views
            views_y = artist_y + 45
            draw.text(
                (title_x, views_y),
                badge_text,
                font=self.font_views,
                fill=GRAY
            )

            # ====== STEP 8: DURATION BADGE (Top Right) ======
            # Like YouTube Music duration badge
            badge_w = 100
            badge_h = 40
            badge_x = W - badge_w - 20
            badge_y = 20
            
            # Background for duration badge
            draw.rectangle(
                [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
                fill=(0, 0, 0, 200)
            )
            
            # Duration text in badge
            draw.text(
                (badge_x + 15, badge_y + 8),
                duration,
                font=self.font_sub,
                fill=WHITE
            )

            # ====== STEP 9: BOTTOM RIGHT WATERMARK ======
            # Small bot name
            draw.text(
                (W - 200, H - 40),
                "YouTube Music",
                font=self.font_sub,
                fill=(80, 80, 80)
            )

            # Save
            bg.save(output)
            try:
                os.remove(temp)
            except:
                pass

            return output

        except Exception as e:
            print(f"❌ Render error: {e}")
            return self._render_fallback(temp, output, song)

    # ========================================
    # FALLBACK RENDER
    # ========================================

    def _render_fallback(self, temp, output, song):
        """Simple fallback thumbnail"""
        try:
            img = Image.open(temp).convert("RGB").resize((W, H))
            
            # Dark overlay
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 150))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay)
            
            draw = ImageDraw.Draw(img)
            
            # Title
            title = safe_text(getattr(song, "title", "Unknown"))[:60]
            try:
                font1 = ImageFont.truetype("arial.ttf", 60)
                font2 = ImageFont.truetype("arial.ttf", 30)
            except:
                font1 = ImageFont.load_default()
                font2 = ImageFont.load_default()
            
            # Title with outline
            for dx, dy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                draw.text((60+dx, 500+dy), title, font=font1, fill=(0, 0, 0))
            draw.text((60, 500), title, font=font1, fill=WHITE)
            
            # Artist
            artist = safe_text(getattr(song, "channel_name", "Unknown"))[:30]
            draw.text((60, 580), f"🎵 {artist}", font=font2, fill=LIGHT_GRAY)
            
            img.save(output)
            return output
            
        except Exception as e:
            print(f"❌ Fallback error: {e}")
            return None


# ========================================
# CONVENIENCE FUNCTIONS
# ========================================

async def generate_thumbnail(song) -> str:
    """Generate YouTube Music-style thumbnail"""
    thumb = Thumbnail()
    await thumb.start()
    result = await thumb.generate(song)
    await thumb.close()
    return result


# ========================================
# TEST CODE
# ========================================

if __name__ == "__main__":
    async def test():
        # Test song
        song = Track(
            id="dQw4w9WgXcQ",
            title="Never Gonna Give You Up",
            thumbnail="https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
            channel_name="Rick Astley",
            view_count="1500000000",
            duration="3:33"
        )
        
        result = await generate_thumbnail(song)
        if result:
            print(f"✅ Thumbnail saved: {result}")
        else:
            print("❌ Failed")
    
    asyncio.run(test())
