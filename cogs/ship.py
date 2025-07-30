import logging
import discord
import ai_handler
import json
from discord.ext import commands
from discord import app_commands
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

	async def analyse_compatibility(self, user1_data: Dict, user2_data: Dict) -> Dict[str, Any]:
		prompt = f"""
Analyse the compatibility between these two Discord users and return ONLY a JSON response with this exact format:

{{
	"percentage": <number between 0-100>,
	"message": "<fun ship message based on the percentage>",
	"ship_name": "<only ONE ship name, based on the two user's display name / username (whatever works best)>"
}}

User 1 Info:
- Username: {user1_data["info"]["username"]}
- Display Name: {user1_data["info"]["display_name"]}
- Recent Messages: {user1_data["messages"][:5]}

User 2 Info:
- Username: {user2_data["info"]["username"]}
- Display Name: {user2_data["info"]["display_name"]}
- Recent Messages: {user2_data["messages"][:5]}

Guidelines for percentage:
- 0-20%: Not compatible, different vibes
- 21-40%: Some potential but challenges
- 41-60%: Decent compatibility
- 61-80%: Good match for each other
- 81-100%: Perfect match, practically soulmates

Make the message fun and playful. For high percentages, say they're meant to be. For low percentages, suggest they're better as friends. Keep it light-hearted and appropriate. You may use emoticons like :3, T-T, <3, </3, etc...

Return ONLY the JSON, no other text. ONLY the JSON.
"""

		response = ""

		# i hate working with jsons
		try:
			response = await ai_handler.generate_ai_response(prompt)
			response = response.strip()

			start_idx = response.find("{")
			end_idx = response.find("}") + 1

			if start_idx != -1 and end_idx != 0:
				json_str = response[start_idx:end_idx]
				return json.loads(json_str)
			else:
				return {
					"percentage": 50,
					"message": "The cosmic forces are unclear... maybe try again? :3"
				}
		except json.JSONDecodeError:
			logger.warning(f"Failed to parse AI JSON response: {response}")
			return {
				"percentage": 50,
				"message": "The cosmic forces are unclear... maybe try again? :3"
			}
		except Exception as e:
			logger.error(f"Error in ship cog: {e}")
			return {
				"percentage": -100,
				"message": "Shipper broke, maybe I need to go find some love T-T"
			}

	@app_commands.command(name="ship", description="Ship two users and see how compatible they are <3!")
	@app_commands.describe(
		user1="First user to ship",
		user2="Second user to ship"
	)
	async def ship_command(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
		await interaction.response.defer()

		try:
			if user1.bot or user2.bot:
				await interaction.followup.send("Can't ship bots! They don't have feelings... yet :3", ephemeral=True)
				return

			if user1 == user2:
				await interaction.followup.send("Can't ship someone with themselves! That's just self-love :3", ephemeral=True)
				return

			user1_messages = await self.get_user_messages(user1)
			user2_messages = await self.get_user_messages(user2)

			user1_data = {
				"info": self.get_user_info(user1),
				"messages": user1_messages
			}

			user2_data = {
				"info": self.get_user_info(user2),
				"messages": user2_messages
			}

			result = await self.analyse_compatibility(user1_data, user2_data)

			percentage = result["percentage"]
			filled_hearts = int(percentage / 10)
			empty_hearts = 10 - filled_hearts
			heart_bar = ("💖" * filled_hearts) + ("🤍" * empty_hearts)

			if percentage >= 80:
				colour = 0xFF1493
			elif percentage >= 60:
				colour = 0xFF69B4
			elif percentage >= 40:
				colour = 0xFFA500
			else:
				colour = 0x808080

			embed = discord.Embed(
				title="💕 Ship Analysis 💕",
				color=colour
			)

			embed.add_field(
				name=f"{result["ship_name"]} ({user1.display_name} × {user2.display_name})",
				value=f"**{percentage}%** compatible!\n{heart_bar}",
				inline=False
			)

			embed.add_field(
				name="Analysis",
				value=result["message"],
				inline=False
			)

			await interaction.followup.send(embed=embed)
		except Exception as e:
			logger.error(f"Error in ship command: {e}")
			await interaction.followup.send("Internal error!", ephemeral=True)

async def setup(bot):
	await bot.add_cog(ShipCog(bot))
