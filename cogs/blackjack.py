import random
import discord
from discord.ext import commands

class Game:
	def __init__(self, user_id):
		self.user_id = user_id
		self.deck = []
		self.player_hand = []
		self.dealer_hand = []
		self.game_over = False

		self.deal_initial_cards()

	def create_deck(self):
		suits = ["♠", "♥", "♦", "♣"]
		ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
		deck = [(rank, suit) for suit in suits for rank in ranks]

		random.shuffle(deck)

		return deck

	def deal_card(self):
		return self.deck.pop()

	def deal_initial_cards(self):
		self.deck = self.create_deck()

		self.player_hand = [self.deal_card(), self.deal_card()]
		self.dealer_hand = [self.deal_card(), self.deal_card()]

	def calculate_hand_value(self, hand):
		value = 0
		aces = 0

		for rank, suit in hand:
			if rank in ["J", "Q", "K"]:
				value += 10
			elif rank == "A":
				aces += 1
				value += 11
			else:
				value += int(rank)

		while value > 21 and aces > 0:
			value -= 10
			aces -= 1

		return value

	def hand_to_string(self, hand, hide_first=False):
		if hide_first:
			return f"🎴 {hand[1][0]}{hand[1][1]}"
		return " ".join([f"{rank}{suit}" for rank, suit in hand])

	def create_embed(self):
		embed = discord.Embed(title=f"🃏 Blackjack v. {self.user_id}", color=0x2F3136)

		dealer_value = self.calculate_hand_value(self.dealer_hand)
		player_value = self.calculate_hand_value(self.player_hand)

		if self.game_over:
			embed.add_field(
				name=f"Dealer ({dealer_value})",
				value=self.hand_to_string(self.dealer_hand),
				inline=False
			)
		else:
			embed.add_field(
				name=f"Dealer (?)",
				value=self.hand_to_string(self.dealer_hand, hide_first=True),
				inline=False
			)

		embed.add_field(
			name=f"{self.user_id} ({player_value})",
			value=self.hand_to_string(self.player_hand),
			inline=False
		)

		if self.game_over:
			if player_value > 21:
				embed.add_field(name="Result", value=f"**💥 {self.user_id} Bust!**")
			elif dealer_value > 21:
				embed.add_field(name="Result", value=f"**💥 Dealer Bust! 🏆 {self.user_id} wins!**")
			elif player_value > dealer_value:
				embed.add_field(name="Result", value=f"**🏆 {self.user_id} wins!**")
			elif player_value < dealer_value:
				embed.add_field(name="Result", value=f"**❌ Dealer wins!**")
			else:
				embed.add_field(name="Result", value=f"🤝 Inconclusive!")

		return embed

class View(discord.ui.View):
	def __init__(self, game, cog):
		super().__init__(timeout=300)
		self.game = game
		self.cog = cog

	@discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="👉")
	async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.game.user_id:
			await interaction.response.send_message("this is not ur game", ephemeral=True)

		self.game.player_hand.append(self.game.deal_card())
		player_value = self.game.calculate_hand_value(self.game.player_hand)

		if player_value > 21:
			self.game.game_over = True
			self.clear_items()
			if self.game.user_id in self.cog.active_games:
				del self.cog.active_games[self.game.user_id]

		await interaction.response.edit_message(embed=self.game.create_embed(), view=self)

	@discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary, emoji="✋")
	async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.game.user_id:
			await interaction.response.send_message("this is not ur game", ephemeral=True)

		while self.game.calculate_hand_value(self.game.dealer_hand) < 17:
			self.game.dealer_hand.append(self.game.deal_card())

		self.game.game_over = True
		self.clear_items()
		if self.game.user_id in self.cog.active_games:
			del self.cog.active_games[self.game.user_id]

		await interaction.response.edit_message(embed=self.game.create_embed(), view=self)

	async def on_timeout(self):
		if self.game.user_id in self.cog.active_games:
			del self.cog.active_games[self.game.user_id]

class Cog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.active_games = {}

	@discord.app_commands.command(name="blackjack", description="Start a new game of blackjack!")
	async def blackjack(self, interaction: discord.Interaction):
		if interaction.user.id in self.active_games:
			await interaction.response.send_message("you already have a game going :p", ephemeral=True)
			return

		game = Game(interaction.user.id)
		self.active_games[interaction.user.id] = game

		player_value = game.calculate_hand_value(game.player_hand)
		if player_value == 21:
			game.game_over = True
			embed = game.create_embed()
			embed.add_field(name="Result", value=f"**🏆 {interaction.user.id} wins!**", inline=False)
			del self.active_games[interaction.user.id]
			await interaction.response.send_message(embed=embed)
			return

		view = View(game, self)
		await interaction.response.send_message(embed=game.create_embed(), view=view)

	@discord.app_commands.command(name="quit_blackjack", description="Quit the current game of blackjack")
	async def quit_blackjack(self, interaction: discord.Interaction):
		if interaction.user.id not in self.active_games:
			await interaction.response.send_message("you don't have a game going :(", ephemeral=True)
			return

		del self.active_games[interaction.user.id]
		await interaction.response.send_message("quit!", ephemeral=True)

async def setup(bot):
	await bot.add_cog(Cog(bot))
