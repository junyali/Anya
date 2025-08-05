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
from typing import List

logger = logging.getLogger(__name__)

# TODO: probably better to make this a separate module
class Card:
	def __init__(self, suit: str, rank: str, value: int):
		self.suit = suit
		self.rank = rank
		self.value = value

	def __str__(self) -> str:
		return f"{self.rank}{self.suit}"

	@property
	def display_name(self):
		return f"{self.rank} of {self.suit}"

class BlackjackHand:
	def __init__(self):
		self.cards: List[Card] = []

	def add_card(self, card: Card):
		self.cards.append(card)

	def get_value(self) -> int:
		total = 0
		aces = 0

		for card in self.cards:
			if card.rank == "A":
				aces += 1
				total += 11
			else:
				total += card.value

		while total > 21 and aces > 0:
			total -= 10
			aces -= 1

		return total

	def is_blackjack(self) -> bool:
		return len(self.cards) == 2 and self.get_value() == 21

	def is_bust(self) -> bool:
		return self.get_value() > 21

	def display(self, hide_first: bool = False) -> str:
		if hide_first and len(self.cards) > 0:
			visible_cards = ["🃏"] + [str(card) for card in self.cards[1:]]
			# hopefully this looks right :sob:
			return " ".join(visible_cards) + f" (? + {self.get_value() - self.cards[0].value})"
		else:
			return " ".join(str(card) for card in self.cards) + f" ({self.get_value()})"

class BlackjackGame:
	def __init__(self):
		self.deck = []
		self.player_hand = BlackjackHand()
		self.dealer_hand = BlackjackHand()
		self.game_over = False
		self.player_won = None

class BlackjackView(discord.ui.View):
	def __init(self, user_id: int):
		super().__init__(timeout=config.GAMES_CONFIG.GAME_TIMEOUT)
		self.user_id = user_id
		self.game = BlackjackGame()

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
- Include tsundere personality (act annoyed but secretly caring)
- MUST include "DURATION_PLACEHOLDER" in the tsundere_message (but DO NOT put seconds, minutes, hours, etc)
- Can reference what they posted if you want
- Make your own variations based off the response examples below if you want

Message: {message}

Tsundere response examples:
- "Hmph! You asked for it, baka! Enjoy your DURATION_PLACEHOLDER timeout! 😤"
- "I-It's not like I wanted to timeout you or anything! DURATION_PLACEHOLDER should teach you! 😤"
- "S-Stupid! Did you really think you'd get away with that?! DURATION_PLACEHOLDER for you!"
- "Ugh! Fine! Take your DURATION_PLACEHOLDER and think about what you've done, idiot!"
- "D-Don't get the wrong idea! I'm only timing you out for DURATION_PLACEHOLDER because I have to!"
- "You're so annoying! Here's your DURATION_PLACEHOLDER timeout! Maybe that'll teach you!"
- "N-Not that I'm enjoying this... but DURATION_PLACEHOLDER timeout seems fitting, baka!"

Respond with ONLY this JSON format (copy format EXACTLY):
{{"duration_seconds": <number between 1-86400>,"tsundere_message": "<Your message with DURATION_PLACEHOLDER where duration would normally go, under 128 characters>"}}

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
				response_message = parsed_json.get("tsundere_message", "Hmph! DURATION_PLACEHOLDER timeout for you, baka! 😤")

				duration = max(60, min(86400, duration))

				return duration, response_message
			else:
				raise ValueError("No valid JSON response found")
		except Exception as e:
			logger.warning(f"AI 691 Response failed: {e}")
			duration = random.randint(300, 7200)
			response_message = "Hmph! DURATION_PLACEHOLDER timeout for you, baka! 😤"

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
			if "DURATION_PLACEHOLDER" in tsundere_message:
				tsundere_message = tsundere_message.replace("DURATION_PLACEHOLDER", duration_str)
			timeout_until = discord.utils.utcnow() + datetime.timedelta(seconds=timeout_seconds)

			if not config.GAMES_CONFIG.TIMEOUT_VISUAL:
				await member.timeout(timeout_until, reason="691")

			embed = discord.Embed(
				title=f"{random.choice(self.timeout_emojis)} r/691",
				description=tsundere_message,
				color=0xFF6B9D
			)

			embed.add_field(
				name=f"📝 Post by {member.display_name}",
				value=f"```{message.content}```",
				inline=False
			)

			embed.add_field(
				name=f"🔓 Release",
				value=f"<t:{int(timeout_until.timestamp())}:R>",
				inline=True
			)

			embed.set_footer(
				text="The bot has spoken.",
				icon_url=member.display_avatar.url
			)

			thumbnail_url = await self.get_random_anime_image("https://api.waifu.pics/sfw/waifu")
			if thumbnail_url:
				embed.set_thumbnail(url=thumbnail_url)

			await message.reply(embed=embed, mention_author=False)
		except discord.Forbidden as e:
			logger.error(f"691 Game error: {e}")
		except discord.HTTPException as e:
			logger.error(f"691 Game error: {e}")
		except Exception as e:
			logger.error(f"691 Game error: {e}")

async def setup(bot: commands.Bot):
	await bot.add_cog(GamesCog(bot))
