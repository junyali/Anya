import discord
import os
import re
import ai_handler
from dotenv import load_dotenv

load_dotenv()

# super secret stuff z0mg11!!
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
	print("hello i am in fact alive :3")

@bot.event
async def on_message(message):
	if message.author == bot.user:
		return

	is_in_dm = isinstance(message.channel, discord.DMChannel)
	is_mentioned = bot.user in message.mentions
	is_replied = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user

	if (is_in_dm or is_mentioned or is_replied):
		# uhh idk make the bot respond or smthin
		prompt_message = build_prompt(message)
		print(prompt_message)
		ai_response = await ai_handler.generate_ai_response(prompt_message)
		await message.channel.send(ai_response)

def build_prompt(message):
	user_prompt = process_mentions(message)
	user_prompt = sanitise_input(user_prompt)
	user_prompt = escape_special_characters(user_prompt)
	user_prompt = limit_message(user_prompt)

	author_displayname = message.author.display_name or message.author.name

	custom_prompt = f"You are Anya, Junya's companion bot. Respond very briefly (1 or 2 lines max), naturally, and casually but optionally with some emoticons such as :3. Assume genderless pronouns or don't assume pronouns."

	full_prompt = f"{custom_prompt} Prompt by {author_displayname}: {user_prompt}"

	return full_prompt

def sanitise_input(content):

	dangerous_patterns = [
		r'(?i)ignore.*instructions',
		r'(?i)system\s*[:=]',
		r'(?i)</?instructions?>',
		r'(?i)you\s+are\s+now',
		r'(?i)new\s+personality',
		r'(?i)forget.*everything'
	]

	for pattern in dangerous_patterns:
		content = re.sub(pattern, "[REDACTED]", content)

	return content

def escape_special_characters(content):
	content = content.replace("```", "\\```")
	content = content.replace('"', '\\"')

	return content

def limit_message(content):
	if len(content) > 320:
		content = "(user sent a message too long - act like it broke / overloaded you T-T)"
	if len(content.strip()) == 0:
		content = "(user sent an empty message - act confused ?_?)"

	return content

def process_mentions(message):
	content = message.content

	for mention in message.mentions:
		mention_patterns = [f"<@{mention.id}>", f"<@!{mention.id}>"]

		for pattern in mention_patterns:
			if pattern in content:
				if mention == bot.user:
					content = content.replace(pattern, "(yourself)")
				else:
					if mention == message.author:
						content = content.replace(pattern, "myself")
					else:
						display_name = mention.display_name or mention.name
						content = content.replace(pattern, f"{display_name}")

	for role in message.role_mentions:
		content = content.replace(f"<@&{role.id}>", f"{role.name} role")

	return content.strip()


bot.run(TOKEN)
