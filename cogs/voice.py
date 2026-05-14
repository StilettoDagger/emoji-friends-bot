import discord
from discord.ext import commands, tasks
from utils.state import active_status_messages
from utils.helpers import update_specific_status_message, update_vc_status

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_update_loop.start()

    def cog_unload(self):
        self.status_update_loop.cancel()

    @tasks.loop(seconds=10)
    async def status_update_loop(self):
        for msg_id in list(active_status_messages.keys()):
            await update_specific_status_message(msg_id)

    @status_update_loop.before_loop
    async def before_status_update_loop(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if after.channel:
            await update_vc_status(after.channel)
        
        if before.channel and before.channel != after.channel:
            await update_vc_status(before.channel)

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
