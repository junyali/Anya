import discord
import logging

from discord.ext import commands
from discord import app_commands
from moderation_handler import ModerationAction, ModerationValidator

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

	@app_commands.command(name="exile", description="exile a user from the server")
	@app_commands.describe(
		user="the user to exile",
		reason="the reason for the exile",
		delete_messages="messages to delete from the last X days"
	)
	@has_moderation_permissions()
	async def ban_command(self,
		interaction: discord.Interaction,
		user: discord.Member,
		reason: str = "no reason provided",
		delete_messages: app_commands.Range[int, 0, 7] = 0
	):
		await interaction.response.defer(ephemeral=True)

		moderator = interaction.user
		guild = interaction.guild
		bot_member = guild.me

		if not ModerationValidator.has_permission_for_action(moderator, ModerationAction.BAN):
			await interaction.followup.send("you don't have perms :(", ephemeral=True)
			return

		if not ModerationValidator.has_permission_for_action(bot_member, ModerationAction.BAN):
			await interaction.followup.send("i don't have perms :(", ephemeral=True)

		can_moderate, error_msg = ModerationValidator.can_moderate_user(guild, moderator, user, bot_member)
		if not can_moderate:
			await interaction.followup.send(error_msg, ephemeral=True)
			return

		try:
			await user.ban(reason=reason, delete_message_days=delete_messages)

			embed = discord.Embed(
				title="🔨 user exiled",
				description=f"**{user.mention}** has been exiled for {reason}",
				color=0xE74C3C
			)

			await interaction.followup.send(embed=embed)
			await interaction.followup.send("executed successfully! :3", ephemeral=True)
		except discord.Forbidden:
			await interaction.followup.send("no permissions T-T", ephemeral=True)
		except discord.HTTPException as e:
			await interaction.followup.send(f"failed to ban: {e}", ephemeral=True)

	@app_commands.command(name="kick", description="kick a user from the server")
	@app_commands.describe(
		user="the user to kick",
		reason="the reason for the kick"
	)
	@has_moderation_permissions()
	async def kick_command(self,
		interaction: discord.Interaction,
		user: discord.Member,
		reason: str = "no reason provided"
	):
		await interaction.response.defer(ephemeral=True)

		moderator = interaction.user
		guild = interaction.guild
		bot_member = guild.me

		if not ModerationValidator.has_permission_for_action(moderator, ModerationAction.KICK):
			await interaction.followup.send("you don't have perms :(", ephemeral=True)
			return

		if not ModerationValidator.has_permission_for_action(bot_member, ModerationAction.KICK):
			await interaction.followup.send("i don't have perms :(", ephemeral=True)
			return

		can_moderate, error_msg = ModerationValidator.can_moderate_user(guild, moderator, user, bot_member)
		if not can_moderate:
			await interaction.followup.send(error_msg, ephemeral=True)
			return

		try:
			await user.kick(reason=reason)

			embed = discord.Embed(
				title="💢 user kicked",
				description=f"**{user.mention}** has been kicked for {reason}",
				color=0xF39C12
			)

			await interaction.followup.send(embed=embed)
			await interaction.followup.send("executed successfully! :3", ephemeral=True)
		except discord.Forbidden:
			await interaction.followup.send("no permissions T-T", ephemeral=True)
		except discord.HTTPException as e:
			await interaction.followup.send(f"failed to kick: {e}", ephemeral=True)


async def setup_bot(bot: commands.Bot):
	await bot.add_cog(ModerationCog(bot))
