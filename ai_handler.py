import aiohttp
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

class AIHandler:
	def __init__(self, api_url: str = "https://ai.hackclub.com/chat/completions"):
		self.api_url = api_url
		self.session = None

	async def __aenter__(self):
		self.session = aiohttp.ClientSession()
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		if self.session:
			await self.session.close()

	async def _make_request(self, messages: list) -> Optional[str]:
		if not self.session:
			self.session = aiohttp.ClientSession()

		try:
			async with self.session.post(
				self.api_url,
				headers={
					"Content-Type": "application/json"
				},
				json={
					"messages": messages
				},
				timeout=aiohttp.ClientTimeout(total=5)
			) as response:
				response.raise_for_status()
				data = await response.json()
				return data.get(
					"choices",
					[{}]
				)[0].get(
					"message",
					{}
				).get(
					"content"
				)

		except asyncio.TimeoutError:
			logger.warning("Timed out request")
			return None
		except aiohttp.ClientError as e:
			logger.error(e)
			return None
		except Exception as e:
			logger.error(e)
			return None

	async def generate_response(self, user_message: str) -> str:
		messages = [
			{
				"role": "user",
				"content": user_message
			}
		]

		response = await self._make_request(messages)

		return response or "*timed out*"

	async def generate_emoji(self, user_message: str) -> str:
		prompt = f"Based on this message: '{user_message}', response with exactly ONE relevant standard unicode emoji if you can find a suitable one. If no emoji fits well, respond with ONLY 'none'. Only return the emoji character or 'none', NOTHING else."

		messages = [
			{
				"role": "user",
				"content": prompt
			}
		]

		response = await self._make_request(messages)

		return response or "none"

	async def close(self):
		if self.session:
			await self.session.close()

_ai_handler = AIHandler()

async def generate_ai_response(user_message: str) -> str:
	return await _ai_handler.generate_response(user_message)

async def generate_ai_emoji(user_message: str) -> str:
	return await _ai_handler.generate_emoji(user_message)

async def close():
	await _ai_handler.close()
