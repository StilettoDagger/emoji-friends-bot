import discord
from discord import app_commands
from discord.ext import commands
import os
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

@bot.tree.command(name="set_emoji", description="Assign an emoji to your username for VC status")
@app_commands.describe(emoji="The emoji you want to display when in a VC")
async def set_emoji(interaction: discord.Interaction, emoji: str):
    # Basic validation: check if it's a single emoji or custom emoji string
    # For now, we'll store whatever string they provide, but ideally we'd validate.
    database.set_user_emoji(interaction.user.id, emoji)
    await interaction.response.send_message(f"Your emoji has been set to: {emoji}", ephemeral=True)

@bot.tree.command(name="toggle_status", description="Toggle dynamic emoji status for the current Voice Channel")
async def toggle_status(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You must be in a voice channel to use this command.", ephemeral=True)
        return

    channel = interaction.user.voice.channel
    # Check permissions (Manage Channels or similar)
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("You need 'Manage Channels' permissions to toggle status tracking.", ephemeral=True)
        return

    is_enabled = database.toggle_vc_status(channel.id)
    status_msg = "enabled" if is_enabled else "disabled"
    
    # If disabling, clear the status
    if not is_enabled:
        await channel.edit(status=None)
        
    await interaction.response.send_message(f"Emoji status tracking has been **{status_msg}** for {channel.name}.", ephemeral=True)

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
