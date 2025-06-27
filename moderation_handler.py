import discord
import ai_handler
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass

class ModerationAction(Enum):
	BAN = "ban"
	KICK = "kick"
	TIMEOUT = "timeout"
	UNBAN = "unban"
	UNTIMEOUT = "untimeout"

@dataclass
class ModerationIntent:
	action: ModerationAction
	target_id: Optional[int]
	target_mention: Optional[str]
	reason: Optional[str]
	duration: Optional[int] = None # minutes
	confidence: float = 0.0

class ModerationParse:
	MODERATION_KEYWORDS = {
		"ban": ModerationAction.BAN,
		"kick": ModerationAction.KICK,
		"deport": ModerationAction.KICK, # for legal reasons this is a joke :skull:
		"timeout": ModerationAction.TIMEOUT,
		"time out": ModerationAction.TIMEOUT,
		"mute": ModerationAction.TIMEOUT,
		"silence": ModerationAction.TIMEOUT,
		"shush": ModerationAction.TIMEOUT,
		"unban": ModerationAction.UNBAN,
		"un ban": ModerationAction.UNBAN,
		"pardon": ModerationAction.UNBAN,
		"untimeout": ModerationAction.UNTIMEOUT,
		"unmute": ModerationAction.UNTIMEOUT
	}

	@classmethod
	def has_moderation_keywords(cls, message: str) -> bool:
		message_lower = message.lower()
		return any(keyword in message_lower for keyword in cls.MODERATION_KEYWORDS.keys())

	@classmethod
	async def parse_moderation_intent(cls, message: str) -> Optional[ModerationIntent]:
		parsing_prompt = f""

class ModerationValidator:
	@staticmethod
	def can_moderate_user(guild: discord.Guild, moderator: discord.member, target: discord.Member, bot: discord.Member) -> tuple[bool, str]:
		if target.id == moderator.id:
			return False, "can't do that to urself buddy"

		if target.id == bot.id:
			return False, "i am IMMUNE!!!"

		if target.id == guild.owner_id:
			return False, "hey dont do that to the owner :("

		if moderator.id == guild.owner_id:
			return True, ""

		if moderator.top_role <= target.top_role:
			return False, "your league is too low lol"

		if bot.top_role <= target.top_role:
			return False, "my league is too low lol"

		return True, ""

	@staticmethod
	def has_permission_for_action(member: discord.Member, action: ModerationAction) -> bool:
		permission_map = {
			ModerationAction.BAN: member.guild_permissions.ban_members,
			ModerationAction.UNBAN: member.guild_permissions.ban_members,
			ModerationAction.KICK: member.guild_permissions.kick_members,
			ModerationAction.TIMEOUT: member.guild_permissions.moderate_members,
			ModerationAction.UNTIMEOUT: member.guild_permissions.moderate_members
		}

		return permission_map.get(
			action,
			False
		)

class ModerationConfirmationView(discord.ui.View):
	def __init__(self, intent: ModerationIntent, original_message: discord.Message):
		super().__init__(timeout=30.0)
		self.intent = intent
		self.original_message = original_message
		self.confirmed = False

	@discord.ui.button(label="Execute Moderation", style=discord.ButtonStyle.danger, emoji="⚠")
	async def confirm_moderation(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.original_message.author.id:
			await interaction.response.send_message("only the executor can confirm", ephemeral=True)
			return

		await interaction.response.defer()
		await self._execute_moderation(interaction)
		self.confirmed = True
		self.stop()

	@discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
	async def cancel_moderation(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.original_message.author.id:
			await interaction.response.send_message("only the executor can cancel", ephemeral=True)

		await interaction.response.edit_message("cancelled", view=None)
		self.stop()

	discord.ui.button(label="Chat", style=discord.ButtonStyle.success, emoji="💬")
	async def normal_chat(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.original_message.author.id:
			await interaction.response.send_message("only the executor can do this", ephemeral=True)
			return

		await interaction.response.defer()

		from main import AnyaBot
		bot_instance = interaction.client
		if hasattr(bot_instance, "_build_prompt"):
			prompt = bot_instance._build_prompt(self.original_message)
			ai_response = await ai_handler.generate_ai_response(prompt)
			await interaction.send_message(ai_response)

		self.stop()

