import discord
from discord import app_commands
from discord.ext import commands

from src.utils import database
from src.utils.helpers import is_single_emoji, update_vc_status, update_specific_status_message
from src.utils.state import active_status_messages

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_user_status", description="Assign an emoji and text to another user's VC status")
    @app_commands.describe(target_user="The user to update", emoji_input="The single emoji to display (Unicode or Custom)", text_input="The text to display next to the emoji")
    @app_commands.default_permissions(manage_channels=True)
    async def set_user_status_cmd(self, interaction: discord.Interaction, target_user: discord.Member, emoji_input: str, text_input: str = None):
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

        if target_user.voice and target_user.voice.channel:
            await update_vc_status(target_user.voice.channel)

    @app_commands.command(name="clear_user_status", description="Remove another user's assigned emoji and text from their VC status")
    @app_commands.describe(target_user="The user to update")
    @app_commands.default_permissions(manage_channels=True)
    async def clear_user_status_cmd(self, interaction: discord.Interaction, target_user: discord.Member):
        database.set_user_status(target_user.id, None, None)

        await interaction.response.send_message(f"Status for {target_user.display_name} has been removed.", ephemeral=True)

        if target_user.voice and target_user.voice.channel:
            await update_vc_status(target_user.voice.channel)

    @app_commands.command(name="toggle_status", description="Toggle dynamic emoji status for a Voice Channel")
    @app_commands.describe(channel="The voice channel to toggle (defaults to your current channel)")
    async def toggle_status(self, interaction: discord.Interaction, channel: discord.VoiceChannel = None):
        target_channel = channel or (interaction.user.voice.channel if interaction.user.voice else None)
        
        if not target_channel:
            await interaction.response.send_message("Please specify a channel or join one to use this command.", ephemeral=True)
            return

        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("You need 'Manage Channels' permissions to toggle status tracking.", ephemeral=True)
            return

        is_enabled = database.toggle_vc_status(target_channel.id)
        status_msg = "enabled" if is_enabled else "disabled"
        
        await interaction.response.send_message(f"Emoji status tracking has been **{status_msg}** for {target_channel.name}.", ephemeral=True)

        if not is_enabled:
            await target_channel.edit(status=None)
            for msg_id, data in list(active_status_messages.items()):
                if data['channel'].id == target_channel.id:
                    await update_specific_status_message(msg_id)
        else:
            await update_vc_status(target_channel)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
