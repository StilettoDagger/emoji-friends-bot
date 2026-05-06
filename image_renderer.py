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
    except Exception as e:
        print(f"Error fetching image from {url}: {e}")
    return None

def get_unicode_hex(char):
    # Twemoji uses hex without leading zeros
    hex_code = "-".join(hex(ord(c))[2:] for c in char)
    return hex_code.replace("-fe0f", "")

USER_POSITIONS = {}

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
        font = ImageFont.truetype("assets/Roboto-Regular.ttf", 32)
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
            else:
                hex_code = get_unicode_hex(emj)
                url = f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{hex_code}.png"
                
            tasks.append(fetch_image(session, url))
            
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
        if user_id in USER_POSITIONS:
            x, y = USER_POSITIONS[user_id]
            # Drift randomly by up to 30 pixels in any direction
            x += random.randint(-30, 30)
            y += random.randint(-30, 30)
            # Clamp to bounds
            x = max(min_x, min(x, max_x))
            y = max(min_y, min(y, max_y))
            USER_POSITIONS[user_id] = (x, y)
        else:
            x = random.randint(min_x, max_x)
            y = random.randint(min_y, max_y)
            USER_POSITIONS[user_id] = (x, y)
        
        # Paste emoji using the emoji image itself as the alpha mask
        bg.paste(emj_img, (x, y), emj_img)
        
        # Draw speech bubble if there is text
        if txt:
            # calculate text size
            bbox = draw.textbbox((0, 0), txt, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            padding = 20
            bubble_w = text_w + padding * 2
            bubble_h = text_h + padding * 2
            
            # Position bubble above emoji
            bubble_x = x + 36 - bubble_w // 2
            bubble_y = y - bubble_h - 25
            
            # Keep bubble within bounds
            if bubble_x < 20: bubble_x = 20
            if bubble_x + bubble_w > width - 20: bubble_x = width - bubble_w - 20
            if bubble_y < 20: bubble_y = y + 72 + 25  # Draw below if not enough space
            
            cx = bubble_x + bubble_w / 2
            cy = bubble_y + bubble_h / 2
            
            # Draw cloud puffs around the text bounds
            num_puffs = max(6, int((bubble_w + bubble_h) / 25))
            for j in range(num_puffs):
                angle = j * (2 * math.pi / num_puffs)
                # varying puff radius
                radius = 15 + 10 * abs(math.sin(angle * 2.5))
                # offset from center
                px = cx + (bubble_w / 2 - padding / 2) * math.cos(angle)
                py = cy + (bubble_h / 2 - padding / 2) * math.sin(angle)
                
                draw.ellipse([px - radius, py - radius, px + radius, py + radius], fill=(255, 255, 255, 240))
                
            # Fill the center body
            draw.ellipse([bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h], fill=(255, 255, 255, 240))
            
            # Draw trail of decreasing circles to the emoji (thought/cloud bubble style)
            if bubble_y < y: # Cloud is above emoji
                draw.ellipse([x + 36 - 8, bubble_y + bubble_h, x + 36 + 8, bubble_y + bubble_h + 16], fill=(255, 255, 255, 240))
                draw.ellipse([x + 36 - 4, bubble_y + bubble_h + 20, x + 36 + 4, bubble_y + bubble_h + 28], fill=(255, 255, 255, 240))
            else: # Below
                draw.ellipse([x + 36 - 8, bubble_y - 16, x + 36 + 8, bubble_y], fill=(255, 255, 255, 240))
                draw.ellipse([x + 36 - 4, bubble_y - 28, x + 36 + 4, bubble_y - 20], fill=(255, 255, 255, 240))
            
            # Draw text
            draw.text((bubble_x + padding, bubble_y + padding), txt, fill=(0, 0, 0, 255), font=font)
            
    # Save to BytesIO
    out_io = io.BytesIO()
    bg.save(out_io, format="PNG")
    out_io.seek(0)
    return out_io
