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

