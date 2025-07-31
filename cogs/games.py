import logging
import ai_handler
import json
import random
import re
import config
import discord
import datetime
import aiohttp
from discord.ext import commands

logger = logging.getLogger(__name__)

class GamesCog(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

		self.timeout_emojis = ["⏰", "🚪", "💥", "🔨", "⚡", "🎲", "💀", "🎯"]

	def format_duration(self, seconds: int) -> str:
		if seconds < 60:
			return f"{seconds} second{"s" if seconds != 1 else ""}"
		elif seconds < 3600:
			minutes = seconds // 60
			remaining_seconds = seconds % 60
			if remaining_seconds == 0:
				return f"{minutes} minute{"s" if minutes != 1 else ""}"
			else:
				return f"{minutes}m {remaining_seconds}s"
		else:
			hours = seconds // 3600
			remaining_minutes = (seconds % 3600) // 60
			if remaining_minutes == 0:
				return f"{hours} hour{"s" if hours != 1 else ""}"
			else:
				return f"{hours}h {remaining_minutes}m"

	async def get_ai_691_response(self, message: str) -> tuple[int, str]:
		prompt = f"""
A 691 game has been triggered by posting "r/691". Generate a JSON response with timeout duration and tsundere message.
The 691 game: Users post "r/691" and get randomly timed out. Your job is to decide duration based on the quality of the message and create a tsundere anime girl response.

Duration guidelines:
- Most boring / low-effort posts: Shorter timeouts (only a few minutes or so)
- Posts that are funny, creative or invoke chaos: Longer timeouts (a few hours?)
- Absolute legendary posts / feeling mean: Very, very long timeouts (up to 24 hours)
- Use variety! Don't always pick the same ranges or any arbitrary numbers
- Duration in SECONDS only. I repeat, SECONDS, NOT HOURS, up to 86400 seconds.

Message: {message}

Tsundere response examples:
- "Hmph! You asked for it, baka! Enjoy your {{}} timeout! 😤"
- "I-It's not like I wanted to timeout you or anything! {{}} should teach you! 😤"
- "S-Stupid! Did you really think you'd get away with that?! {{}} for you!"
- "Ugh! Fine! Take your {{}} and think about what you've done, idiot!"
- "D-Don't get the wrong idea! I'm only timing you out for {{}} because I have to!"
- "You're so annoying! Here's your {{}} timeout! Maybe that'll teach you!"
- "N-Not that I'm enjoying this... but {{}} timeout seems fitting, baka!"

Respond with ONLY this JSON format:
{{
	"duration_seconds": <number between 1-86400>,
	"tsundere_message": "<message with {{}} where duration goes, under 128 characters>"
}}

JSON only, no other text.
"""

		try:
			response = await ai_handler.generate_ai_response(prompt)
			response = response.strip()

			start_idx = response.find("{")
			end_idx = response.find("}") + 1

			if start_idx != -1 and end_idx > start_idx:
				json_str = response[start_idx:end_idx]
				parsed_json = json.loads(json_str)

				duration = int(parsed_json.get("duration_seconds", 1800))
				response_message = parsed_json.get("tsundere_message", "Hmph! {} timeout for you, baka! 😤")

				duration = max(60, min(86400, duration))

				return duration, response_message
			else:
				raise ValueError("No valid JSON response found")
		except Exception as e:
			logger.warning(f"AI 691 Response failed: {e}")
			duration = random.randint(300, 7200)
			response_message = "Hmph! {} timeout for you, baka! 😤"

			return duration, response_message

	def is_691_trigger(self, content: str) -> bool:
		pattern = r'^r/691'
		return bool(re.match(pattern, content.strip(), re.IGNORECASE))

	async def get_random_anime_image(self, url) -> str:
		try:
			async with aiohttp.ClientSession() as session:
				async with session.get(url) as response:
					if response.status == 200:
						data = await response.json()
						return data.get("url", "")
		except Exception as e:
			logger.warning(f"Failed to get anime image: {e}")
		return ""

	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		if message.author.bot or not message.guild:
			return

		if not self.is_691_trigger(message.content):
			return

		member = message.author

		if not config.GAMES_CONFIG.TIMEOUT_VISUAL:
			if not message.guild.me.guild_permissions.moderate_members:
				return

			if isinstance(member, discord.Member):
				if member.id == message.guild.owner_id:
					return
				if member.top_role >= message.guild.me.top_role:
					return

		try:
			timeout_seconds, tsundere_message = await self.get_ai_691_response(message.content)
			duration_str = self.format_duration(timeout_seconds)
			tsundere_message = tsundere_message.format(duration_str)
			timeout_until = discord.utils.utcnow() + datetime.timedelta(seconds=timeout_seconds)

			if not config.GAMES_CONFIG.TIMEOUT_VISUAL:
				await member.timeout(timeout_until, reason="691")

			embed = discord.Embed(
				title=f"{random.choice(self.timeout_emojis)} r/691",
				description=tsundere_message,
				color=0xFF6B9D
			)

			embed.add_field(
				name=f"📝 Post by {member.mention}",
				value=f"```{message.content}```",
				inline=False
			)

			embed.set_footer(
				text=f"🔓 Released <t:{int(timeout_until.timestamp())}:R>",
				icon_url=member.display_avatar.url
			)

			thumbnail_url = await self.get_random_anime_image("https://api.waifu.pics/sfw/waifu")
			if thumbnail_url:
				embed.set_thumbnail(url=thumbnail_url)

			await message.reply(embed=embed, mention_author=False)
		except discord.Forbidden:
			pass
		except discord.HTTPException:
			pass
		except Exception as e:
			logger.error(f"691 Game error: {e}")

async def setup(bot: commands.Bot):
	await bot.add_cog(GamesCog(bot))
