import re
import emoji
import discord
from src.utils import database

# Custom Discord emoji regex: <:name:id> or <a:name:id>
CUSTOM_EMOJI_REGEX = re.compile(r"^<a?:\w+:\d+>$")

def is_single_emoji(text: str) -> bool:
    # Check if it's a single Unicode emoji
    if emoji.emoji_count(text) == 1 and len(emoji.replace_emoji(text, "")) == 0:
        return True
    # Check if it's a single custom Discord emoji
    if CUSTOM_EMOJI_REGEX.match(text):
        return True
    return False

def generate_status_embed(channel: discord.VoiceChannel) -> discord.Embed:
    is_enabled = database.is_vc_enabled(channel.id)
    enabled_str = "🟢 **Enabled**" if is_enabled else "🔴 **Disabled**"

    users_info = []
    for member in sorted(channel.members, key=lambda m: m.name.lower()):
        emoji_char, text = database.get_user_status(member.id)
        if emoji_char and text:
            status_str = f"{emoji_char} *{text}*"
        elif emoji_char:
            status_str = f"{emoji_char}"
        else:
            status_str = "*(no status)*"
        users_info.append(f"👤 **{member.display_name}**: {status_str}")

    embed = discord.Embed(title=f"🎙️ {channel.name} Status", color=discord.Color.blue())
    embed.add_field(name="Tracking", value=enabled_str, inline=False)

    if users_info:
        embed.description = "\n".join(users_info)
    else:
        embed.description = "*No users found in this channel.*"

    return embed
import uuid
from src.utils import image_renderer
from src.utils.state import active_status_messages

async def update_specific_status_message(msg_id):
    if msg_id not in active_status_messages:
        return
        
    data = active_status_messages[msg_id]
    message = data['message']
    channel = data['channel']
    theme = data['theme']
    
    try:
        from src.ui.environment_view import EnvironmentView
        embed = generate_status_embed(channel)
        
        author_id = data['author_id']
        view = EnvironmentView(author_id, theme)
        
        user_statuses = []
        for member in sorted(channel.members, key=lambda m: m.name.lower()):
            emoji_char, text = database.get_user_status(member.id)
            if emoji_char:
                user_statuses.append((member.id, emoji_char, text))
                
        if user_statuses:
            image_io = await image_renderer.generate_room_image(user_statuses, background_name=theme)
            filename = f"room_{uuid.uuid4().hex[:8]}.png"
            file = discord.File(fp=image_io, filename=filename)
            embed.set_image(url=f"attachment://{filename}")
            await message.edit(embed=embed, attachments=[file], view=view)
        else:
            await message.edit(embed=embed, attachments=[], view=view)
    except discord.NotFound:
        del active_status_messages[msg_id]
    except discord.HTTPException as e:
        print(f"Failed to update status message {msg_id}: {e}")

async def update_vc_status(channel):
    # Update all active embeds for this channel
    for msg_id, data in list(active_status_messages.items()):
        if data['channel'].id == channel.id:
            await update_specific_status_message(msg_id)

    if not database.is_vc_enabled(channel.id):
        return

    emojis = []
    for member in sorted(channel.members, key=lambda m: m.name.lower()):
        emoji, _ = database.get_user_status(member.id)
        if emoji:
            emoji_item = f"{emoji}"
            emojis.append(emoji_item)
    
    emoji_str = " ".join(emojis) if emojis else None
    
    try:
        await channel.edit(status=emoji_str)
    except discord.Forbidden:
        print(f"Missing permissions to edit status in {channel.name}")
    except discord.HTTPException as e:
        print(f"Failed to update status in {channel.name}: {e}")
