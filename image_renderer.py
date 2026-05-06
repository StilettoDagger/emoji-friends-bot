import io
import re
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import asyncio
import emoji
import random
import math

CUSTOM_EMOJI_REGEX = re.compile(r"^<a?:(\w+):(\d+)>$")

IMAGE_CACHE = {}

async def fetch_image(session, url):
    if url in IMAGE_CACHE:
        return IMAGE_CACHE[url]
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.read()
                IMAGE_CACHE[url] = data
                return data
            else:
                # Cache failures to prevent repeated 404s
                IMAGE_CACHE[url] = None
                return None
    except Exception as e:
        print(f"Error fetching image from {url}: {e}")
        IMAGE_CACHE[url] = None
    return None

def get_unicode_hex(char):
    h_raw = "-".join(hex(ord(c))[2:] for c in char)
    h_stripped = h_raw.replace("-fe0f", "")
    h_appended = h_stripped + "-fe0f"
    # Return unique variants (try raw first, then stripped, then appended)
    return list(dict.fromkeys([h_raw, h_stripped, h_appended]))

async def generate_room_image(user_statuses):
    """
    user_statuses: list of tuples (user_id, emoji_str, text_str)
    """
    # Load background
    try:
        bg = Image.open("assets/background.png").convert("RGBA")
    except FileNotFoundError:
        print("Warning: Background not found, using white image.")
        bg = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
        
    width, height = bg.size
    
    # Load font
    try:
        font = ImageFont.truetype("assets/PressStart2P-Regular.ttf", 14)
    except IOError:
        print("Warning: Font not found, using default.")
        font = ImageFont.load_default()

    async with aiohttp.ClientSession() as session:
        tasks = []
        for uid, emj, txt in user_statuses:
            match = CUSTOM_EMOJI_REGEX.match(emj)
            if match:
                emoji_id = match.group(2)
                # For animated emojis, we'll download the static png version
                url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
                tasks.append(fetch_image(session, url))
            else:
                hex_list = get_unicode_hex(emj)
                
                async def fetch_twemoji_with_fallback(session, hexes):
                    for h in hexes:
                        url = f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{h}.png"
                        img_data = await fetch_image(session, url)
                        if img_data:
                            return img_data
                    return None
                
                tasks.append(fetch_twemoji_with_fallback(session, hex_list))
            
        emoji_images_data = await asyncio.gather(*tasks)
        
    draw = ImageDraw.Draw(bg)
    
    # Floor area boundaries (approximate based on standard isometric room)
    min_x, max_x = int(width * 0.2), int(width * 0.8)
    min_y, max_y = int(height * 0.5), int(height * 0.8)
    
    for i, (emj_data, (user_id, emj, txt)) in enumerate(zip(emoji_images_data, user_statuses)):
        if not emj_data:
            print(f"Skipping emoji {emj} as image data was not downloaded.")
            continue
            
        try:
            emj_img = Image.open(io.BytesIO(emj_data)).convert("RGBA")
            # Resize emoji
            emj_img = emj_img.resize((72, 72), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"Failed to load emoji image data: {e}")
            continue
            
        # Determine position
        # Teleport to random positions each frame
        x = random.randint(min_x, max_x)
        y = random.randint(min_y, max_y)
        
        # Paste emoji using the emoji image itself as the alpha mask
        bg.paste(emj_img, (x, y), emj_img)
        
        # Draw speech bubble if there is text
        if txt:
            # calculate text size
            bbox = draw.textbbox((0, 0), txt, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            padding = 15
            bubble_w = text_w + padding * 2
            bubble_h = text_h + padding * 2
            
            # Position bubble above emoji
            bubble_x = x + 36 - bubble_w // 2
            bubble_y = y - bubble_h - 20
            
            # Keep bubble within bounds
            if bubble_x < 20: bubble_x = 20
            if bubble_x + bubble_w > width - 20: bubble_x = width - bubble_w - 20
            if bubble_y < 20: bubble_y = y + 72 + 20  # Draw below if not enough space
            
            border_w = 3
            draw.rectangle([bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=border_w)
            
            tail_x = x + 36
            tail_w = 16
            tail_h = 16
            
            if bubble_y < y: # Bubble is above emoji
                pts_black = [(tail_x - tail_w/2 - border_w, bubble_y + bubble_h),
                             (tail_x, bubble_y + bubble_h + tail_h + border_w),
                             (tail_x + tail_w/2 + border_w, bubble_y + bubble_h)]
                pts_white = [(tail_x - tail_w/2, bubble_y + bubble_h - border_w - 1),
                             (tail_x, bubble_y + bubble_h + tail_h),
                             (tail_x + tail_w/2, bubble_y + bubble_h - border_w - 1)]
                draw.polygon(pts_black, fill=(0, 0, 0, 255))
                draw.polygon(pts_white, fill=(255, 255, 255, 255))
            else: # Below
                pts_black = [(tail_x - tail_w/2 - border_w, bubble_y),
                             (tail_x, bubble_y - tail_h - border_w),
                             (tail_x + tail_w/2 + border_w, bubble_y)]
                pts_white = [(tail_x - tail_w/2, bubble_y + border_w + 1),
                             (tail_x, bubble_y - tail_h),
                             (tail_x + tail_w/2, bubble_y + border_w + 1)]
                draw.polygon(pts_black, fill=(0, 0, 0, 255))
                draw.polygon(pts_white, fill=(255, 255, 255, 255))
            
            # Draw text
            draw.text((bubble_x + padding, bubble_y + padding), txt, fill=(0, 0, 0, 255), font=font)
            
    # Save to BytesIO
    out_io = io.BytesIO()
    bg.save(out_io, format="PNG")
    out_io.seek(0)
    return out_io
