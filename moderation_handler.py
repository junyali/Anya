import json
import re

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
		parsing_prompt = f"""
Parse this Discord moderation request and respond with ONLY a JSON object with these fields:
- "action": one of: ban, kick, timeout, unban, untimeout
- "target_mention": the exact mention string (like <@123>) if found, otherwise null
- "reason": the reason give, or null if none
- "duration": duration in minutes for timeouts, or null
- "confidence": confidence score between 0.0 and 1.0 (1 = very certain this is a moderation request)
Message to parse: "{message}"
Examples:
"ban <@123> for spamming" -> {{"action": "ban", "target_mention": "<@123>", "reason": "for spamming", "duration": null, "confidence": 0.9}}
"timeout <@badperson> 10 minutes being mean" -> {{"action": "timeout", "target_mention": "<@badperson>", "reason": "being mean", "duration": 10, "confidence": 0.8}}

JSON Response only:
"""

		try:
			ai_response = await ai_handler.generate_ai_response(parsing_prompt)
			parsed_data = json.loads(ai_response.strip())

			target_id = None
			target_mention = parsed_data.get("target_mention")
			if target_mention:
				mention_match = re.search(r'<@!?(\d+)>', target_mention)
				if mention_match:
					target_id = int(mention_match.group(1))

			action_str = parsed_data.get("action", "").lower()
			if action_str not in [action.value for action in ModerationAction]:
				return None

			action = ModerationAction[action_str]
			confidence = float(parsed_data.get("confidence", 0.0))

			if confidence < 0.5:
				return None

			return ModerationIntent(
				action=action,
				target_id=target_id,
				target_mention=target_mention,
				reason=parsed_data.get("reason"),
				duration=parsed_data.get("duration"),
				confidence=confidence
			)

		except (json.JSONDecodeError, ValueError, KeyError) as e:
			print(e)
			return None

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

	async def _execute_moderation(self, interaction: discord.Interaction):
		guild = interaction.guild
		moderator = interaction.user
		bot_member = guild.me

		if not self.intent.target_id:
			await interaction.response.send_message("target not identified :(", ephemeral=True)
			return

		try:
			target = guild.get_member(self.intent.target_id)

			if not target and self.intent.action not in [ModerationAction.UNBAN]:
				target = await guild.fetch_member(self.intent.target_id)

			if not target and self.intent.action not in [ModerationAction.BAN]:
				await interaction.response.send_message("target not in server :(", ephemeral=True)
				return

		except discord.NotFound:
			if self.intent.action not in [ModerationAction.UNBAN]:
				await interaction.response.send_message("target not found :(", ephemeral=True)
				return

		if not ModerationValidator.has_permission_for_action(moderator, self.intent.action):
			await interaction.response.send_message("DENIED.", ephemeral=True)
			return

		if not ModerationValidator.has_permission_for_action(bot_member, self.intent.action):
			await interaction.response.send_message("i lack permissions to perform this :(", ephemeral=True)
			return

		target = guild.get_member(self.intent.target_id)

		if target and self.intent.action != ModerationAction.UNBAN:
			can_moderate, error_msg = ModerationValidator.can_moderate_user(guild, moderator, target, bot_member)
			if not can_moderate:
				await interaction.response.send_message(error_msg, ephemeral=True)
				return

		reason = self.intent.reason or "idk"
		try:
			if self.intent.action == ModerationAction.BAN:
				await target.ban(reason=reason, delete_message_days=0)
				action_text = f"**Banned** {target.mention} for {reason}"
			elif self.intent.action == ModerationAction.KICK:
				await target.kick(reason=reason)
				action_text = f"**Kicked** {target.mention} for {reason}"
			elif self.intent.action == ModerationAction.TIMEOUT:
				import datetime
				duration = self.intent.duration or 10
				timeout_until = discord.utils.utcnow() + datetime.timedelta(minutes=duration)
				await target.timeout(timeout_until, reason=reason)
				action_text = f"**Timed Out** {target.mention} for {reason} for {duration} minutes"
			elif self.intent.action == ModerationAction.UNBAN:
				banned_users = [entry async for entry in guild.bans()]
				ban_entry = next((entry for entry in banned_users if entry.user.id == self.intent.target_id), None)
				if ban_entry:
					await guild.unban(ban_entry.user, reason=reason)
					action_text = f"**Unbanned** {target.mention} for {reason}"
				else:
					raise discord.NotFound("target not banned")
			elif self.intent.action == ModerationAction.UNTIMEOUT:
				await target.timeout(None, reason=reason)
				action_text = f"**Untimed Out** {target.mention} for {reason}"
			else:
				action_text = f"**{self.intent.action.value.title()}** performed"

			await interaction.edit_original_response(view=None, content=action_text)

		except discord.Forbidden:
			await interaction.response.send_message("no permissions", ephemeral=True)
		except discord.HTTPException as e:
			await interaction.response.send_message(e, ephemeral=True)

	async def on_timeout(self):
		try:
			await self.original_message.delete()
		except discord.HTTPException:
			pass

