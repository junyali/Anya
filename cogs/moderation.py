import discord
import logging

from discord.ext import commands
from discord import app_commands

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
	datefmt="[%Y-%m-%d %H:%M:%S]"
)

class ModerationCog(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	def has_moderation_permissions(self):
		async def predicate(interaction: discord.Interaction) -> bool:
			if not interaction.guild:
				await interaction.followup.send("only in servers T-T", ephemeral=True)
				return False

			member = interaction.guild.get_member(interaction.user.id)
			if not member:
				await interaction.followup.send("something went wrong T-T", ephemeral=True)
				return False

			return True
		return app_commands.check(predicate)

async def setup_bot(bot: commands.Bot):
	await bot.add_cog(ModerationCog(bot))
