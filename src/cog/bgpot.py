import asyncio

from discord.ext import commands, tasks

from core.clogs import logger
from processing.run_command import run_command, CMDError


class BgPot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bgpot.clear_exception_types()
        self.bgpot.add_exception_type(CMDError)
        self.bgpot.start()

    def cog_unload(self):
        self.bgpot.cancel()

    @tasks.loop()
    async def bgpot(self):
        await run_command("node", "/bgutil-ytdlp-pot-provider/server/build/main.js")
        logger.warning("bgpot closed.")