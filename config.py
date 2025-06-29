import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class BotConfig:
	TOKEN: str = os.getenv("BOT_TOKEN")
	COMMAND_PREFIX: str = "#"

	# rate limiting stuff
	RATE_LIMIT_MESSAGES: int = 30
	RATE_LIMIT_WINDOW: int = 60
	RATE_LIMIT_MESSAGES_LOCAL: int = 10
	RATE_LIMIT_WINDOW_LOCAL: int = 60

	MAX_MESSAGE_LENGTH = 320

@dataclass
class RoleplayConfig:
	MAX_SESSIONS_PER_USER: int = 1
	MAX_GLOBAL_SESSIONS: int = 10
	MAX_SESSIONS_PER_DAY: int = 5

	MAX_MESSAGES_PER_WINDOW: int = 10
	MESSAGE_RATE_WINDOW: int = 600

	SESSION_TIMEOUT_MINUTES: int = 15
	CLEANUP_INTERVAL_SECONDS: int = 300
	THREAD_AUTO_ARCHIVE_MINUTES: int = 60

	MAX_CHARACTER_NAME_LENGTH: int = 64
	MAX_CHARACTER_PROMPT_LENGTH: int = 1024
	MAX_AVATAR_URL_LENGTH: int = 512
	MAX_BASE64_AVATAR_LENGTH: int = (8 * 1024) - 1
	MAX_USER_MESSAGE_LENGTH: int = 512

	MAX_CONVERSATION_HISTORY: int = 20
	CONTEXT_WINDOW_SIZE: int = 10
	MAX_AI_RESPONSE_LENGTH: int = 256

@dataclass
class ModerationConfig:
	MIN_CONFIDENCE_THRESHOLD: float = 0.5
	FALLBACK_CONFIDENCE: float = 0.6

	MAX_REASON_LENGTH: int = 256
	MAX_DURATION_MINUTES: int = 28 * 24 * 60

BOT_CONFIG = BotConfig()
ROLEPLAY_CONFIG = RoleplayConfig()
MODERATION_CONFIG = ModerationConfig()
