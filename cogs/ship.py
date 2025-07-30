import logging
from discord.ext import commands

logger = logging.getLogger(__name__)

class ShipCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot


