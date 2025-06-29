import discord
import logging
import time
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from discord.ext import commands
from collections import defaultdict, deque

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

class RateLimiter:
	def __init__(self):
		self.user_sessions = defaultdict(int)
		self.user_messages = defaultdict(deque)
		self.user_commands = defaultdict(deque)

		self.global_sessions = 0

	def can_create_session(self, user_id: int) -> tuple[bool, str]:
		now = time.time()

		user_commands = self.user_commands[user_id]
		while user_commands and user_commands[0] < now - 86400:
			user_commands.popleft()

		if len(user_commands) >= 3:
			return False, "you can only have 1 roleplays at a time >:("

		if self.user_sessions[user_id] >= 1:
			return False, "you already have a roleplay in progress.."

		if self.global_sessions >= 10:
			return False, "too many active roleplays at the moment..."

		user_commands.append(now)
		return True, ""

	def can_send_message(self, user_id: int) -> tuple[bool, str]:
		now = time.time()

		user_messages = self.user_messages[user_id]
		while user_messages and user_messages[0] < now - 300:
			user_messages.popleft()

		if len(user_messages) >= 10:
			return False, "you're sending too many messages!"

		user_messages.append(now)
		return True, ""

	def add_session(self, user_id: int):
		self.user_sessions[user_id] += 1
		self.global_sessions +=1

	def remove_session(self, user_id: int):
		if self.user_sessions[user_id] > 0:
			self.user_sessions[user_id] -= 1

		if self.global_sessions > 0:
			self.global_sessions -= 1

class RoleplayCog(commands.Cog):
	def __init(self, bot: commands.Bot):
		self.bot = bot
		self.active_sessions: Dict[int, RoleplaySession] = {}

async def setup(bot: commands.Bot):
	await bot.add_cog(RoleplayCog(bot))
