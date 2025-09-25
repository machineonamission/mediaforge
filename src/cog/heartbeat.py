import asyncio

from discord.ext import commands, tasks

import config
from core.clogs import logger
from processing.run_command import run_command, CMDError
from utils.common import fetch


class Heartbeat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if config.heartbeaturl is not None:
            # all exceptions should be handled
            self.heartbeat.clear_exception_types()
            self.heartbeat.add_exception_type(Exception)
            self.heartbeat.start()

    def cog_unload(self):
        self.heartbeat.cancel()

    @tasks.loop(seconds=config.heartbeatfrequency)
    async def heartbeat(self):
        resp = await fetch(config.heartbeaturl)
        logger.debug(f"Successfully sent heartbeat. {resp}")