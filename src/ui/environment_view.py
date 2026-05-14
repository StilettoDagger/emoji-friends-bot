import discord
from src.utils import database
from src.utils.state import active_status_messages

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
            # Late import to avoid circular dependency
            from src.utils.helpers import update_specific_status_message
            await update_specific_status_message(msg_id)
        else:
            await interaction.response.send_message("This status message is no longer active. Run `/status` again.", ephemeral=True)
