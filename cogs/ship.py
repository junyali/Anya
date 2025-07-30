import logging
import discord
from discord.ext import commands
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ShipCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	async def get_user_messages(self, user: discord.Member, limit: int = 10) -> List[str]:
		messages = []

		for channel in user.guild.text_channels:
			if not channel.permissions_for(user.guild.me).read_message_history and not channel.permissions_for(user.guild.me).read_messages:
				continue

			try:
				async for message in channel.history(limit=50):
					if message.author == user and not message.author.bot:
						messages.append({
							"content": message.content[:128] + "[TRUNCATED]" if len(message.content) > 128 else message.content,
							"timestamp": message.created_at.isoformat(),
							"channel": channel.name
						})

						if len(messages) >= limit:
							break

				if len(messages) >= limit:
					break

			except discord.Forbidden:
				continue
			except Exception as e:
				logger.warning(f"Error read from {channel.name}: {e}")
				continue

		messages.sort(key=lambda x: x["timestamp"], reverse=True)
		return [msg["content"] for msg in messages[:limit]]

	def get_user_info(self, user: discord.Member) -> Dict[str, Any]:
		return {
			"username": user.name,
			"display_name": user.display_name,
			"nickname": user.nick,
			"joined_server": user.joined_at.isoformat() if user.joined_at else None,
			"account_created": user.created_at.isoformat(),
			"roles": [role.name for role in user.roles if role.name != "@everyone"],
			"status": str(user.status),
			"activity": str(user.activity) if user.activity else None
		}

async def setup(bot):
	await bot.add_cog(ShipCog(bot))
