import discord
import os
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
	user_prompt = clean_message(message)

	author_displayname = message.author.display_name
	author_username = message.author.name

	custom_prompt = f"You are Anya, Junya's companion discord bot. Respond very briefly (1 or 2 lines max) but optionally with some emoticons such as :3."

	full_prompt = f"{custom_prompt} Prompt by {author_displayname}: {user_prompt}"

	return full_prompt

def clean_message(message):
	content = message.content

	for mention in message.mentions:
		if mention == bot.user:
			content = content.replace(f"<@{mention.id}>", "").strip()
			content = content.replace(f"<@!{mention.id}>", "").strip()

	return content.strip()


bot.run(TOKEN)
