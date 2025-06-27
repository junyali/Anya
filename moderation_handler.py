import discord
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
