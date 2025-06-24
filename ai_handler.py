import requests
import json

async def generate_ai_response(user_message):
	try:
		response = requests.post(
			"https://ai.hackclub.com/chat/completions",
			headers={
				"Content-Type": "application/json"
			},
			json={
				"messages": [
					{
						"role": "user",
						"content": user_message
					}
				]
			}
		)

		response.raise_for_status()

		ai_response = response.json()
		return ai_response.get(
			"choices",
			[{}]
		)[0].get("message", {}).get("content", "response not available")

	except requests.RequestException as e:
		print(e)
		return "umm i did not work :p"

async def generate_ai_emoji(user_message):
	try:
		response = requests.post(
			"https://ai.hackclub.com/chat/completions",
			headers={
				"Content-Type": "application/json"
			},
			json={
				"messages": [
					{
						"role": "user",
						"content": f"Based on this message: '{user_message}', respond with exactly ONE relevant standard unicode emoji if you can find a suitable one. If no emoji fits well, respond with 'none'. Only return the emoji character or 'none', nothing else."
					}
				]
			}
		)

		response.raise_for_status()

		ai_response = response.json()

		return ai_response.get(
			"choices",
			[{}]
		)[0].get("message", {}).get("content", "none")

	except requests.RequestException as e:
		print(e)
		return "none"
