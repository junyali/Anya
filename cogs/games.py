import logging
import ai_handler
import json
import random
import re
import config
import discord
import datetime
import aiohttp
from discord import app_commands
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
		self.deck = self._create_deck()
		self.player_hand = BlackjackHand()
		self.dealer_hand = BlackjackHand()
		self.game_over = False
		self.player_won = None

		for i in range(2):
			self.player_hand.add_card(self.draw_card())
			self.dealer_hand.add_card(self.draw_card())

	def _create_deck(self) -> List[Card]:
		suits = ["♠", "♥", "♦", "♣"]
		rank_values = [
			("2", 2),
			("3", 3),
			("4", 4),
			("5", 5),
			("6", 6),
			("7", 7),
			("8", 8),
			("9", 9),
			("10", 10),
			("J", 10),
			("Q", 10),
			("K", 10),
			("A", 11)
		]

		deck = []

		for suit in suits:
			for rank, value in rank_values:
				deck.append(Card(suit, rank, value))

		random.shuffle(deck)
		return deck

	def draw_card(self) -> Card:
		return self.deck.pop()

	def player_hit(self):
		self.player_hand.add_card(self.draw_card())
		if self.player_hand.is_bust():
			self.game_over = True
			self.player_won = False

	def player_stand(self):
		while self.dealer_hand.get_value() < 17:
			self.dealer_hand.add_card(self.draw_card())

		self.game_over = True

		player_value = self.player_hand.get_value()
		dealer_value = self.dealer_hand.get_value()

		if self.dealer_hand.is_bust():
			self.player_won = True
		elif player_value > dealer_value:
			self.player_won = True
		elif player_value < dealer_value:
			self.player_won = False
		else:
			self.player_won = None

	def get_game_state(self) -> str:
		player_blackjack = self.player_hand.is_blackjack()
		player_bust = self.player_hand.is_bust()

		dealer_blackjack = self.dealer_hand.is_blackjack()
		dealer_bust = self.dealer_hand.is_bust()

		if player_blackjack and dealer_blackjack:
			return "⚔ Draw!"
		elif player_blackjack:
			return "🎉 Blackjack! You win!"
		elif dealer_blackjack:
			return "💀 Dealer Blackjack! You lose!"
		elif player_bust:
			return "💥 Bust! You lose!"
		elif dealer_bust:
			return "💢 Dealer Bust! You win!"
		elif self.game_over:
			if self.player_won is True:
				return "🎉 You win!"
			elif self.player_won is False:
				return "💀 You lose!"
			else:
				return "⚔ Draw!"
		else:
			return "🎲 Game in progress..."

class BlackjackView(discord.ui.View):
	def __init__(self, user_id: int):
		super().__init__(timeout=config.GAMES_CONFIG.GAME_TIMEOUT)
		self.user_id = user_id
		self.game = BlackjackGame()

		player_blackjack = self.game.player_hand.is_blackjack()
		dealer_blackjack = self.game.dealer_hand.is_blackjack()

		if player_blackjack or dealer_blackjack:
			self.game.game_over = True
			if player_blackjack and not dealer_blackjack:
				self.game.player_won = True
			elif dealer_blackjack and not player_blackjack:
				self.game.player_won = False

	def create_embed(self):
		if self.game.game_over:
			colour = 0x00ff00 if self.game.player_won else 0xff0000 if self.game.player_won is False else 0xffff00
		else:
			colour = 0x3498db

		embed = discord.Embed(
			title="🃏 Blackjack",
			description=self.game.get_game_state(),
			color=colour
		)

		dealer_display = self.game.dealer_hand.display(hide_first=not self.game.game_over)
		embed.add_field(
			name="🤖 Dealer's Hand",
			value=dealer_display,
			inline=False
		)

		# TODO: Make messages personalised to the user
		embed.add_field(
			name="🎯 Your Hand",
			value=self.game.player_hand.display(),
			inline=False
		)

		if self.game.game_over:
			embed.set_footer(text="Game Over!")
		else:
			embed.set_footer(text="Awaiting action..")

		return embed

	async def update_message(self, interaction: discord.Interaction):
		embed = self.create_embed()

		if self.game.game_over:
			for item in self.children:
				item.disabled = True

		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="🎯")
	async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			await interaction.response.send_message("This is not your game! >:(", ephemeral=True)
			return

		if self.game.game_over:
			await interaction.response.send_message("Game already over! >:(", ephemeral=True)
			return

		self.game.player_hit()
		await self.update_message(interaction)

	@discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary, emoji="✋")
	async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			await interaction.response.send_message("This is not your game! >:(", ephemeral=True)
			return

		if self.game.game_over:
			await interaction.response.send_message("Game already over! >:(", ephemeral=True)
			return

		self.game.player_stand()
		await self.update_message(interaction)

	async def on_timeout(self):
		for item in self.children:
			item.disabled = True

		try:
			embed = self.create_embed()
			embed.set_footer(text="⏰ Timed out!")
		except:
			pass



class GamesCog(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

		self.timeout_emojis = ["⏰", "🚪", "💥", "🔨", "⚡", "🎲", "💀", "🎯"]

	@app_commands.command(name="blackjack", description="Play a game of blackjack against Anya!")
	async def blackjack_command(self, interaction: discord.Interaction):
		try:
			view = BlackjackView(interaction.user.id)
			embed = view.create_embed()

			await interaction.response.send_message(embed=embed, view=view)
		except Exception as e:
			logger.error(f"Error occurred starting Blackjack game: {e}")
			await interaction.response.send_message("Internal error occurred!", ephemeral=True)


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
