import json
import re
import logging
import discord
import ai_handler
from typing import Optional
from enum import Enum
from dataclasses import dataclass

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
	datefmt="[%Y-%m-%d %H:%M:%S]"
)

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

class ModerationParser:
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
- "confidence": confidence score between 0.00 and 1.00 (1 = very certain this is a moderation request, 0 = very certain this is NOT a moderation request)
Message to parse: "{message}"
Examples:
"ban <@123> for spamming" -> {{"action": "ban", "target_mention": "<@123>", "reason": "for spamming", "duration": null, "confidence": 0.92}}
"timeout <@badperson> 10 minutes being mean" -> {{"action": "timeout", "target_mention": "<@badperson>", "reason": "being mean", "duration": 10, "confidence": 0.85}}

JSON Response only (NO CODE BLOCKS OR OTHER RESPONSE - PLAINTEXT ONLY):
"""

		try:
			ai_response = await ai_handler.generate_ai_response(parsing_prompt)

			logging.debug(f"Moderation AI response: {ai_response}")

			if not ai_response or ai_response.strip() == "":
				logging.warning("AI returned empty response")
				return None

			ai_response = ai_response.strip()

			json_match = re.search(r'\{.*}', ai_response, re.DOTALL)
			if json_match:
				json_str = json_match.group(0)
			else:
				json_str = ai_response

			parsed_data = json.loads(ai_response.strip())

			if not isinstance(parsed_data, dict):
				logging.warning("AI returned non-JSON Object")
				return None

			action_str = parsed_data.get("action", "").lower()
			if action_str not in [action.value for action in ModerationAction]:
				logging.warning(f"Invalid action: {action_str}")
				return None

			action = ModerationAction(action_str)

			try:
				confidence = float(parsed_data.get("confidence", 0.0))
			except (ValueError, TypeError):
				confidence = 0.0

			if confidence < 0.75:
				logging.debug(f"Confidence too low: {confidence}")
				return None

			target_id = None
			target_mention = parsed_data.get("target_mention")
			if target_mention:
				mention_match = re.search(r'<@!?(\d+)>', target_mention)
				if mention_match:
					target_id = int(mention_match.group(1))

			duration = parsed_data.get("duration")
			if duration is not None:
				try:
					duration = int(duration)
				except (ValueError, TypeError):
					duration = None

			return ModerationIntent(
				action=action,
				target_id=target_id,
				target_mention=target_mention,
				reason=parsed_data.get("reason"),
				duration=parsed_data.get("duration"),
				confidence=confidence
			)

		except json.JSONDecodeError as e:
			logging.warning(f"JSONDecodeError: {e}")
		except (ValueError, KeyError, TypeError) as e:
			logging.warning(f"Unexpected error: {e}")
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
		self.reply_message = None

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
			return

		await interaction.response.defer(ephemeral=True)
		await interaction.followup.send("cancelled!", ephemeral=True)
		await self._cleanup_messages()
		self.stop()

	@discord.ui.button(label="Chat", style=discord.ButtonStyle.success, emoji="💬")
	async def normal_chat(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.original_message.author.id:
			await interaction.response.send_message("only the executor can do this", ephemeral=True)
			return

		await interaction.response.defer()

		bot_instance = interaction.client
		if hasattr(bot_instance, "build_prompt"):
			prompt = bot_instance.build_prompt(self.original_message)
			ai_response = await ai_handler.generate_ai_response(prompt)

			await self.original_message.reply(ai_response)
			await interaction.followup.send("treated as normal chat :3", ephemeral=True)
		else:
			await interaction.followup.send("couldn't process as chat T-T", ephemeral=True)

		await self._cleanup_messages()

		self.stop()

	async def _cleanup_messages(self):
		try:
			if self.reply_message:
				await self.reply_message.delete(view=None)
		except discord.HTTPException:
			pass

	async def _execute_moderation(self, interaction: discord.Interaction):
		guild = interaction.guild
		moderator = interaction.user
		bot_member = guild.me

		if not self.intent.target_id:
			await interaction.followup.send("target not identified :(", ephemeral=True)
			await self._cleanup_messages()
			return

		target = None

		try:
			target = guild.get_member(self.intent.target_id)

			if not target and self.intent.action not in [ModerationAction.UNBAN]:
				try:
					target = await guild.fetch_member(self.intent.target_id)
				except discord.NotFound:
					await interaction.followup.send("target not in server :(", ephemeral=True)
					await self._cleanup_messages()
		except discord.NotFound:
			if self.intent.action not in [ModerationAction.UNBAN]:
				await interaction.followup.send("target not found :(", ephemeral=True)
				await self._cleanup_messages()
				return
		finally:
			if not ModerationValidator.has_permission_for_action(moderator, self.intent.action):
				await interaction.followup.send("DENIED.", ephemeral=True)
				await self._cleanup_messages()
				return

			if not ModerationValidator.has_permission_for_action(bot_member, self.intent.action):
				await interaction.followup.send("i lack permissions to perform this :(", ephemeral=True)
				await self._cleanup_messages()
				return

			if target and self.intent.action != ModerationAction.UNBAN:
				can_moderate, error_msg = ModerationValidator.can_moderate_user(guild, moderator, target, bot_member)
				if not can_moderate:
					await interaction.followup.send(error_msg, ephemeral=True)
					await self._cleanup_messages()
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
					await interaction.followup.send("target not banned", ephemeral=True)
					await self._cleanup_messages()
					return
			elif self.intent.action == ModerationAction.UNTIMEOUT:
				await target.timeout(None, reason=reason)
				action_text = f"**Untimed Out** {target.mention} for {reason}"
			else:
				action_text = f"**{self.intent.action.value.title()}** performed"

			embed = discord.Embed(
				title="executed!!",
				description=action_text,
				color=0x27AE60
			)
			embed.set_footer(text=f"Action by {moderator.mention}")

			await self.original_message.reply(embed=embed)
			await interaction.followup.send("executed successfully! :3", ephemeral=True)
			await self._cleanup_messages()
		except discord.Forbidden:
			await interaction.followup.send("no permissions", ephemeral=True)
			await self._cleanup_messages()
		except discord.HTTPException as e:
			await interaction.followup.send(e, ephemeral=True)
			await self._cleanup_messages()

	async def on_timeout(self):
		try:
			await self.reply_message.followup.send("your request timed out T-T", ephemeral=True)
		except Exception as e:
			logging.warning(f"{e}")

		try:
			if self.reply_message:
				await self.reply_message.delete()
		except discord.HTTPException:
			pass

		try:
			await self.original_message.delete()
		except discord.HTTPException:
			pass


async def handle_potential_moderation(message: discord.Message, bot) -> bool:
	if not message.guild:
		return False

	content = message.content

	if not ModerationParser.has_moderation_keywords(content):
		return False

	intent = await ModerationParser.parse_moderation_intent(content)
	if not intent or intent.confidence < 0.75:
		return False

	embed = discord.Embed(
		title="moderation request??",
		description="might be tweaking but what do u want me to do?",
		color=0xF39C12
	)

	embed.add_field(
		name="action",
		value=f"**{intent.action.value.title()}** {intent.target_mention or "unknown target"}",
		inline=False
	)

	if intent.reason:
		embed.add_field(
			name="reason",
			value=intent.reason,
			inline=False
		)

	if intent.duration:
		embed.add_field(
			name="duration",
			value=f"{intent.duration} minutes",
			inline=False
		)

	embed.add_field(
		name="confidence",
		value=f"{intent.confidence:.0%}",
		inline=True
	)

	embed.set_footer(text="click buttons pls")

	view = ModerationConfirmationView(intent, message)

	try:
		reply_msg = await message.reply(embed=embed, view=view, mention_author=False)
		view.reply_message = reply_msg
	except discord.HTTPException:
		await message.reply(embed=embed, view=view, mention_author=False)

	return True

