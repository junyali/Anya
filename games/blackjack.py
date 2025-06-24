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
				value=self.hand_to_string(self.dealer_hand),
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

