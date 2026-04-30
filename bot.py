import discord
from discord import app_commands
from discord.ext import commands
import os
import re
import emoji
from dotenv import load_dotenv
import database

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

bot = EmojiBot()

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
    
    # If the user is currently in a voice channel, update that channel's status immediately
    if interaction.user.voice and interaction.user.voice.channel:
        await update_vc_status(interaction.user.voice.channel)
        
    status_msg = f"Your status has been set to: {emoji_input}"
    if text_input:
        status_msg += f" {text_input}"
    await interaction.response.send_message(status_msg, ephemeral=True)

@bot.tree.command(name="unset_status", description="Remove your assigned emoji and text from your VC status")
async def unset_status(interaction: discord.Interaction):
    database.set_user_status(interaction.user.id, None, None)

    # If the user is currently in a voice channel, update that channel's status immediately
    if interaction.user.voice and interaction.user.voice.channel:
        await update_vc_status(interaction.user.voice.channel)

    await interaction.response.send_message("Your status has been removed.", ephemeral=True)

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
    
    # If disabling, clear the status
    if not is_enabled:
        await target_channel.edit(status=None)
    else:
        # If enabling, immediately update it
        await update_vc_status(target_channel)
        
    await interaction.response.send_message(f"Emoji status tracking has been **{status_msg}** for {target_channel.name}.", ephemeral=True)

@bot.tree.command(name="status", description="Check if dynamic emoji status is enabled for a Voice Channel")
@app_commands.describe(channel="The voice channel to check (defaults to your current channel)")
async def status(interaction: discord.Interaction, channel: discord.VoiceChannel = None):
    target_channel = channel or (interaction.user.voice.channel if interaction.user.voice else None)

    if not target_channel:
        await interaction.response.send_message("Please specify a channel or join one to use this command.", ephemeral=True)
        return

    is_enabled = database.is_vc_enabled(target_channel.id)
    status_msg = "enabled" if is_enabled else "disabled"

    await interaction.response.send_message(f"Dynamic emoji status for {target_channel.name} is **{status_msg}**.", ephemeral=True)

@bot.tree.command(name="whoami", description="Get your current assigned status")
async def whoami(interaction: discord.Interaction):
    user_id = interaction.user.id
    emoji, text = database.get_user_status(user_id)
    if emoji:
        msg = f"Your assigned status is: {emoji}"
        if text:
            msg += f" {text}"
        await interaction.response.send_message(msg, ephemeral=True)
    else:
        await interaction.response.send_message("You have no assigned status.", ephemeral=True)

@bot.tree.command(name="vc_who", description="List users in a VC and their assigned statuses")
async def vc_who(interaction: discord.Interaction, channel: discord.VoiceChannel = None):
    target_channel = channel or (interaction.user.voice.channel if interaction.user.voice else None)

    if not target_channel:
        await interaction.response.send_message("Please specify a channel or join one to use this command.", ephemeral=True)
        return

    users_info = []
    for member in target_channel.members:
        emoji, text = database.get_user_status(member.id)
        status_str = f"{emoji} {text}" if emoji and text else (emoji or "none")
        users_info.append(f"{member.display_name}: {status_str}")

    if users_info:
        await interaction.response.send_message(f"Users in {target_channel.name}:\n" + "\n".join(users_info), ephemeral=False)
    else:
        await interaction.response.send_message(f"No users found in {target_channel.name}.", ephemeral=True)

@bot.tree.command(name="whois", description="List all users with assigned statuses")
async def whois(interaction: discord.Interaction):
    users_info = []
    for user_id in database.get_all_user_ids():
        emoji, text = database.get_user_status(user_id)
        if emoji:
            status_str = f"{emoji} {text}" if text else emoji
            users_info.append(f"<@{user_id}>: {status_str}")

    if users_info:
        await interaction.response.send_message("Users with assigned statuses:\n" + "\n".join(users_info), ephemeral=False)
    else:
        await interaction.response.send_message("No users have assigned statuses.", ephemeral=True)

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
        "2. `/unset_status` - Remove your assigned status.\n" \
        "3. `/toggle_status [channel]` - Toggle dynamic status for a voice channel (defaults to your current channel).\n"
        "4. `/status [channel]` - Check if dynamic status is enabled for a voice channel (defaults to your current channel).\n"
        "5. `/whoami` - Get your current assigned status.\n"
        "6. `/vc_who [channel]` - List users in a voice channel and their assigned statuses.\n"
        "7. `/top_emojis` - Show the most popular emojis assigned by users.\n"
        "8. `/whois` - List all users with assigned statuses.\n"
        "9. `/help` - Display this help message.\n\n"
        "**Notes:**\n"
        "- You must have 'Manage Channels' permissions to toggle status tracking for a channel.\n"
        "- The bot will automatically update the VC status when users join or leave, as long as it's enabled for that channel."
    )
    await interaction.response.send_message(help_text, ephemeral=True)

async def update_vc_status(channel):
    if not database.is_vc_enabled(channel.id):
        return

    statuses = []
    for member in channel.members:
        emoji, text = database.get_user_status(member.id)
        if emoji:
            status_item = f"{emoji} {text}" if text else emoji
            statuses.append(status_item)
    
    status_str = " ".join(statuses) if statuses else None
    
    try:
        await channel.edit(status=status_str)
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
