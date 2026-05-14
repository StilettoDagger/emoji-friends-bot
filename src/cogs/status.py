import discord
from discord import app_commands
from discord.ext import commands
import uuid

from src.utils import database
from src.utils import image_renderer
from src.utils.helpers import is_single_emoji, generate_status_embed, update_vc_status
from src.utils.state import active_status_messages
from src.ui.environment_view import EnvironmentView

class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_status", description="Assign an emoji and text to your username for VC status")
    @app_commands.describe(emoji_input="The single emoji you want to display (Unicode or Custom)", text_input="The text you want to display next to the emoji")
    async def set_status(self, interaction: discord.Interaction, emoji_input: str, text_input: str = None):
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

    @app_commands.command(name="clear_status", description="Remove your assigned emoji and text from your VC status")
    async def clear_status(self, interaction: discord.Interaction):
        database.set_user_status(interaction.user.id, None, None)

        await interaction.response.send_message("Your status has been removed.", ephemeral=True)

        # If the user is currently in a voice channel, update that channel's status immediately
        if interaction.user.voice and interaction.user.voice.channel:
            await update_vc_status(interaction.user.voice.channel)

    @app_commands.command(name="status", description="Get the status of a VC and its users")
    @app_commands.describe(channel="The voice channel to check (defaults to your current channel)")
    async def status(self, interaction: discord.Interaction, channel: discord.VoiceChannel = None):
        target_channel = channel or (interaction.user.voice.channel if interaction.user.voice else None)

        if not target_channel:
            await interaction.response.send_message("Please specify a channel or join one to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        embed = generate_status_embed(target_channel)
        user_theme = database.get_user_theme(interaction.user.id)
        view = EnvironmentView(interaction.user.id, user_theme)
        
        user_statuses = []
        for member in sorted(target_channel.members, key=lambda m: m.name.lower()):
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

async def setup(bot):
    await bot.add_cog(StatusCog(bot))
