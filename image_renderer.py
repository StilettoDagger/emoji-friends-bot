import io
import re
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import asyncio
import emoji
import random

CUSTOM_EMOJI_REGEX = re.compile(r"^<a?:(\w+):(\d+)>$")

async def fetch_image(session, url):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
    except Exception as e:
        print(f"Error fetching image from {url}: {e}")
    return None

def get_unicode_hex(char):
    # Twemoji uses hex without leading zeros
    return "-".join(hex(ord(c))[2:] for c in char)

async def generate_room_image(user_statuses):
    """
    user_statuses: list of tuples (emoji_str, text_str)
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
        font = ImageFont.truetype("assets/Roboto-Regular.ttf", 24)
    except IOError:
        print("Warning: Font not found, using default.")
        font = ImageFont.load_default()

    async with aiohttp.ClientSession() as session:
        tasks = []
        for emj, txt in user_statuses:
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
    
    for i, (emj_data, (emj, txt)) in enumerate(zip(emoji_images_data, user_statuses)):
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
        # Simple random placement for now
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
            
            padding = 10
            bubble_w = text_w + padding * 2
            bubble_h = text_h + padding * 2
            
            # Position bubble above emoji
            bubble_x = x + 36 - bubble_w // 2
            bubble_y = y - bubble_h - 15
            
            # Keep bubble within bounds
            if bubble_x < 10: bubble_x = 10
            if bubble_x + bubble_w > width - 10: bubble_x = width - bubble_w - 10
            if bubble_y < 10: bubble_y = y + 72 + 15  # Draw below if not enough space
            
            # Draw bubble background (rounded rectangle)
            bubble_rect = [bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h]
            draw.rounded_rectangle(bubble_rect, radius=10, fill=(255, 255, 255, 230), outline=(200, 200, 200, 255), width=2)
            
            # Draw little triangle pointing to emoji
            if bubble_y < y: # Above
                triangle = [
                    (x + 36 - 10, bubble_y + bubble_h),
                    (x + 36 + 10, bubble_y + bubble_h),
                    (x + 36, bubble_y + bubble_h + 15)
                ]
            else: # Below
                triangle = [
                    (x + 36 - 10, bubble_y),
                    (x + 36 + 10, bubble_y),
                    (x + 36, bubble_y - 15)
                ]
                
            draw.polygon(triangle, fill=(255, 255, 255, 230))
            
            # Draw outline for the triangle part
            if bubble_y < y:
                draw.line([(triangle[0][0], triangle[0][1]), (triangle[2][0], triangle[2][1])], fill=(200, 200, 200, 255), width=2)
                draw.line([(triangle[1][0], triangle[1][1]), (triangle[2][0], triangle[2][1])], fill=(200, 200, 200, 255), width=2)
            else:
                draw.line([(triangle[0][0], triangle[0][1]), (triangle[2][0], triangle[2][1])], fill=(200, 200, 200, 255), width=2)
                draw.line([(triangle[1][0], triangle[1][1]), (triangle[2][0], triangle[2][1])], fill=(200, 200, 200, 255), width=2)
            
            # Draw text
            draw.text((bubble_x + padding, bubble_y + padding), txt, fill=(0, 0, 0, 255), font=font)
            
    # Save to BytesIO
    out_io = io.BytesIO()
    bg.save(out_io, format="PNG")
    out_io.seek(0)
    return out_io
