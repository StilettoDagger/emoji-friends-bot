import discord
from discord import app_commands
from discord.ext import commands

from src.utils import database

class InfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="whoami", description="Get your current assigned status")
    async def whoami(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        emoji, text = database.get_user_status(user_id)
        if emoji:
            msg = f"__**Your current status is**__: {emoji}"
            if text:
                msg += f" {text}"
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message("You have no assigned status.", ephemeral=True)

    @app_commands.command(name="whois", description="List all users with assigned statuses")
    async def whois(self, interaction: discord.Interaction):
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

    @app_commands.command(name="top_emojis", description="Show the most popular emojis assigned by users")
    async def top_emojis(self, interaction: discord.Interaction):
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

    @app_commands.command(name="help", description="Get information about how to use the bot")
    async def help_command(self, interaction: discord.Interaction):
        help_text = (
            "**Bot Commands:**\n"
            "1. `/set_status <emoji> [text]` - Set an emoji and optional text to display in your VC status.\n" \
            "2. `/clear_status` - Remove your assigned status.\n" \
            "3. `/set_user_status <user> <emoji> [text]` - (Admin) Set an emoji and text for another user's status.\n" \
            "4. `/clear_user_status <user>` - (Admin) Remove another user's assigned status.\n" \
            "5. `/toggle_status [channel]` - Toggle dynamic status for a voice channel (defaults to your current channel).\n"
            "6. `/status [channel]` - Get the tracking status and a list of users in a voice channel.\n"
            "7. `/whoami` - Get your current assigned status.\n"
            "8. `/top_emojis` - Show the most popular emojis assigned by users.\n"
            "9. `/whois` - List all users with assigned statuses.\n"
            "10. `/help` - Display this help message.\n\n"
            "**Notes:**\n"
            "- You must have 'Manage Channels' permissions to toggle status tracking for a channel, or to set/clear another user's status.\n"
            "- The bot will automatically update the VC status when users join or leave, as long as it's enabled for that channel."
        )
        await interaction.response.send_message(help_text, ephemeral=True)

async def setup(bot):
    await bot.add_cog(InfoCog(bot))
