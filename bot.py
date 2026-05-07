import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import re
import emoji
from dotenv import load_dotenv
import database
import io
import image_renderer
import uuid

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class EmojiBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.voice_states = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Initialize the database
        database.init_db()
        # Sync slash commands
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")
        self.status_update_loop.start()

    @tasks.loop(seconds=10)
    async def status_update_loop(self):
        for msg_id in list(active_status_messages.keys()):
            await update_specific_status_message(msg_id)

    @status_update_loop.before_loop
    async def before_status_update_loop(self):
        await self.wait_until_ready()

bot = EmojiBot()

# Dict structure: {message_id: {'message': message_obj, 'channel': channel_obj, 'theme': 'default', 'author_id': user_id}}
active_status_messages = {}

class ThemeButton(discord.ui.Button):
    def __init__(self, theme_id, label, emoji, is_active):
        style = discord.ButtonStyle.success if is_active else discord.ButtonStyle.secondary
        super().__init__(label=label, emoji=emoji, style=style, disabled=is_active, custom_id=f"theme_{theme_id}")
        self.theme_id = theme_id

    async def callback(self, interaction: discord.Interaction):
        await self.view.handle_theme_change(interaction, self.theme_id)

class EnvironmentView(discord.ui.View):
    def __init__(self, author_id, current_theme):
        super().__init__(timeout=None)
        self.author_id = author_id
        
        themes = {
            "default": {"label": "Home", "emoji": "🏠"},
            "cafe": {"label": "Cozy Cafe", "emoji": "☕"},
            "office": {"label": "Modern Office", "emoji": "🖥️"},
            "park": {"label": "Park Outdoors", "emoji": "🌳"}
        }

        # Add a non-interactive button to act as a label
        lbl_btn = discord.ui.Button(label="🎨 Choose a theme:", style=discord.ButtonStyle.secondary, custom_id="theme_label", disabled=True)
        async def lbl_callback(interaction: discord.Interaction):
            await interaction.response.defer()
        lbl_btn.callback = lbl_callback
        self.add_item(lbl_btn)

        for theme_id, data in themes.items():
            is_active = (theme_id == current_theme)
            self.add_item(ThemeButton(theme_id, data["label"], data["emoji"], is_active))

    async def handle_theme_change(self, interaction: discord.Interaction, theme: str):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the person who generated this status can change its theme. Run `/status` to create your own view!", ephemeral=True)
            return
            
        database.set_user_theme(self.author_id, theme)
        
        msg_id = interaction.message.id
        if msg_id in active_status_messages:
            active_status_messages[msg_id]['theme'] = theme
            await interaction.response.defer()
            await update_specific_status_message(msg_id)
        else:
            await interaction.response.send_message("This status message is no longer active. Run `/status` again.", ephemeral=True)

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

@bot.tree.command(name="set_status", description="Assign an emoji and text to your username for VC status")
@app_commands.describe(emoji_input="The single emoji you want to display (Unicode or Custom)", text_input="The text you want to display next to the emoji")
async def set_status(interaction: discord.Interaction, emoji_input: str, text_input: str = None):
    emoji_input = emoji_input.strip()
    if text_input:
        text_input = text_input.strip()
    
    if not is_single_emoji(emoji_input):
        await interaction.response.send_message("Please provide exactly **one** valid emoji (Unicode or Custom).", ephemeral=True)
        return

    database.set_user_status(interaction.user.id, emoji_input, text_input)
    
    status_msg = f"Your status has been set to: {emoji_input}"
    if text_input:
        status_msg += f" {text_input}"
    await interaction.response.send_message(status_msg, ephemeral=True)

    # If the user is currently in a voice channel, update that channel's status immediately
    if interaction.user.voice and interaction.user.voice.channel:
        await update_vc_status(interaction.user.voice.channel)

@bot.tree.command(name="clear_status", description="Remove your assigned emoji and text from your VC status")
async def clear_status(interaction: discord.Interaction):
    database.set_user_status(interaction.user.id, None, None)

    await interaction.response.send_message("Your status has been removed.", ephemeral=True)

    # If the user is currently in a voice channel, update that channel's status immediately
    if interaction.user.voice and interaction.user.voice.channel:
        await update_vc_status(interaction.user.voice.channel)

@bot.tree.command(name="set_user_status", description="Assign an emoji and text to another user's VC status")
@app_commands.describe(target_user="The user to update", emoji_input="The single emoji to display (Unicode or Custom)", text_input="The text to display next to the emoji")
@app_commands.default_permissions(manage_channels=True)
async def set_user_status_cmd(interaction: discord.Interaction, target_user: discord.Member, emoji_input: str, text_input: str = None):
    emoji_input = emoji_input.strip()
    if text_input:
        text_input = text_input.strip()
    
    if not is_single_emoji(emoji_input):
        await interaction.response.send_message("Please provide exactly **one** valid emoji (Unicode or Custom).", ephemeral=True)
        return

    database.set_user_status(target_user.id, emoji_input, text_input)
    
    status_msg = f"Status for {target_user.display_name} has been set to: {emoji_input}"
    if text_input:
        status_msg += f" {text_input}"
    await interaction.response.send_message(status_msg, ephemeral=True)

    # If the target user is currently in a voice channel, update that channel's status immediately
    if target_user.voice and target_user.voice.channel:
        await update_vc_status(target_user.voice.channel)

@bot.tree.command(name="toggle_status", description="Toggle dynamic emoji status for a Voice Channel")
@app_commands.describe(channel="The voice channel to toggle (defaults to your current channel)")
async def toggle_status(interaction: discord.Interaction, channel: discord.VoiceChannel = None):
    # Use specified channel or the user's current channel
    target_channel = channel or (interaction.user.voice.channel if interaction.user.voice else None)
    
    if not target_channel:
        await interaction.response.send_message("Please specify a channel or join one to use this command.", ephemeral=True)
        return

    # Check permissions (Manage Channels or similar)
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("You need 'Manage Channels' permissions to toggle status tracking.", ephemeral=True)
        return

    is_enabled = database.toggle_vc_status(target_channel.id)
    status_msg = "enabled" if is_enabled else "disabled"
    
    await interaction.response.send_message(f"Emoji status tracking has been **{status_msg}** for {target_channel.name}.", ephemeral=True)

    # If disabling, clear the status
    if not is_enabled:
        await target_channel.edit(status=None)
        # Update all messages for this channel
        for msg_id, data in list(active_status_messages.items()):
            if data['channel'].id == target_channel.id:
                await update_specific_status_message(msg_id)
    else:
        # If enabling, immediately update it
        await update_vc_status(target_channel)

@bot.tree.command(name="status", description="Get the status of a VC and its users")
@app_commands.describe(channel="The voice channel to check (defaults to your current channel)")
async def status(interaction: discord.Interaction, channel: discord.VoiceChannel = None):
    target_channel = channel or (interaction.user.voice.channel if interaction.user.voice else None)

    if not target_channel:
        await interaction.response.send_message("Please specify a channel or join one to use this command.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)

    embed = generate_status_embed(target_channel)
    user_theme = database.get_user_theme(interaction.user.id)
    view = EnvironmentView(interaction.user.id, user_theme)
    
    user_statuses = []
    for member in target_channel.members:
        emoji_char, text = database.get_user_status(member.id)
        if emoji_char:
            user_statuses.append((member.id, emoji_char, text))
            
    if user_statuses:
        image_io = await image_renderer.generate_room_image(user_statuses, background_name=user_theme)
        filename = f"room_{uuid.uuid4().hex[:8]}.png"
        file = discord.File(fp=image_io, filename=filename)
        embed.set_image(url=f"attachment://{filename}")
        await interaction.followup.send(embed=embed, file=file, view=view)
    else:
        await interaction.followup.send(embed=embed, view=view)
    
    # Track this message for auto-updates
    interaction_message = await interaction.original_response()
    try:
        message = await interaction.channel.fetch_message(interaction_message.id)
    except discord.HTTPException:
        message = interaction_message
        
    active_status_messages[message.id] = {
        'message': message,
        'channel': target_channel,
        'theme': user_theme,
        'author_id': interaction.user.id
    }

@bot.tree.command(name="whoami", description="Get your current assigned status")
async def whoami(interaction: discord.Interaction):
    user_id = interaction.user.id
    emoji, text = database.get_user_status(user_id)
    if emoji:
        msg = f"__**Your current status is**__: {emoji}"
        if text:
            msg += f" {text}"
        await interaction.response.send_message(msg, ephemeral=True)
    else:
        await interaction.response.send_message("You have no assigned status.", ephemeral=True)


@bot.tree.command(name="whois", description="List all users with assigned statuses")
async def whois(interaction: discord.Interaction):
    embed = discord.Embed(title="📋 User Status Directory", color=discord.Color.green())
    
    users_info = []
    for user_id in database.get_all_user_ids():
        emoji, text = database.get_user_status(user_id)
        if emoji:
            status_str = f"{emoji} *{text}*" if text else emoji
            users_info.append(f"👤 <@{user_id}>: {status_str}")

    if users_info:
        embed.description = "\n".join(users_info)
    else:
        embed.description = "*No users have assigned statuses.*"

    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="top_emojis", description="Show the most popular emojis assigned by users")
async def top_emojis(interaction: discord.Interaction):
    emoji_counts = {}
    for user_id in database.get_all_user_ids():
        emoji, text = database.get_user_status(user_id)
        if emoji:
            emoji_counts[emoji] = emoji_counts.get(emoji, 0) + 1

    sorted_emojis = sorted(emoji_counts.items(), key=lambda x: x[1], reverse=True)
    if sorted_emojis:
        await interaction.response.send_message("Top assigned emojis:\n" + "\n".join(f"{emoji}: {count}" for emoji, count in sorted_emojis), ephemeral=False)
    else:
        await interaction.response.send_message("No emojis have been assigned.", ephemeral=True)

@bot.tree.command(name="help", description="Get information about how to use the bot")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**Bot Commands:**\n"
        "1. `/set_status <emoji> [text]` - Set an emoji and optional text to display in your VC status.\n" \
        "2. `/clear_status` - Remove your assigned status.\n" \
        "3. `/set_user_status <user> <emoji> [text]` - (Admin) Set an emoji and text for another user's status.\n" \
        "4. `/toggle_status [channel]` - Toggle dynamic status for a voice channel (defaults to your current channel).\n"
        "5. `/status [channel]` - Get the tracking status and a list of users in a voice channel.\n"
        "6. `/whoami` - Get your current assigned status.\n"
        "7. `/top_emojis` - Show the most popular emojis assigned by users.\n"
        "8. `/whois` - List all users with assigned statuses.\n"
        "9. `/help` - Display this help message.\n\n"
        "**Notes:**\n"
        "- You must have 'Manage Channels' permissions to toggle status tracking for a channel or set another user's status.\n"
        "- The bot will automatically update the VC status when users join or leave, as long as it's enabled for that channel."
    )
    await interaction.response.send_message(help_text, ephemeral=True)

def generate_status_embed(channel: discord.VoiceChannel) -> discord.Embed:
    is_enabled = database.is_vc_enabled(channel.id)
    enabled_str = "🟢 **Enabled**" if is_enabled else "🔴 **Disabled**"

    users_info = []
    for member in channel.members:
        emoji, text = database.get_user_status(member.id)
        if emoji and text:
            status_str = f"{emoji} *{text}*"
        elif emoji:
            status_str = f"{emoji}"
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

async def update_specific_status_message(msg_id):
    if msg_id not in active_status_messages:
        return
        
    data = active_status_messages[msg_id]
    message = data['message']
    channel = data['channel']
    theme = data['theme']
    
    try:
        embed = generate_status_embed(channel)
        
        author_id = data['author_id']
        view = EnvironmentView(author_id, theme)
        
        user_statuses = []
        for member in channel.members:
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
    for member in channel.members:
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

@bot.event
async def on_voice_state_update(member, before, after):
    # User joined a VC
    if after.channel:
        await update_vc_status(after.channel)
    
    # User left a VC
    if before.channel and before.channel != after.channel:
        await update_vc_status(before.channel)

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env file.")
    else:
        bot.run(TOKEN)
