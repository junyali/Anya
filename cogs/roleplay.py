import discord
import logging
import time
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from discord.ext import commands

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
	datefmt="[%Y-%m-%d %H:%M:%S]"
)

@dataclass
class RoleplaySession:
	character_name: str
	character_prompt: str
	user_id: int
	thread_id: int
	avatar_url: Optional[str] = None
	messages: List[str] = field(default_factory=list)
	created_at: float = field(default_factory=time.time)
	last_activity: float = field(default_factory=time.time)
	message_count: int = 0

class RoleplayCog(commands.Cog):
	def __init(self, bot: commands.Bot):
		self.bot = bot
		self.active_sessions: Dict[int, RoleplaySession] = {}

async def setup(bot: commands.Bot):
	await bot.add_cog(RoleplayCog(bot))
