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

@bot.tree.command(name="set_emoji", description="Assign an emoji to your username for VC status")
@app_commands.describe(emoji_input="The single emoji you want to display (Unicode or Custom)")
async def set_emoji(interaction: discord.Interaction, emoji_input: str):
    emoji_input = emoji_input.strip()
    
    if not is_single_emoji(emoji_input):
        await interaction.response.send_message("Please provide exactly **one** valid emoji (Unicode or Custom).", ephemeral=True)
        return

    database.set_user_emoji(interaction.user.id, emoji_input)
    await interaction.response.send_message(f"Your emoji has been set to: {emoji_input}", ephemeral=True)

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

async def update_vc_status(channel):
    if not database.is_vc_enabled(channel.id):
        return

    emojis = []
    for member in channel.members:
        emoji = database.get_user_emoji(member.id)
        if emoji:
            emojis.append(emoji)
    
    status_str = " ".join(emojis) if emojis else None
    
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
