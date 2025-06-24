import discord
import os
import requests
import json
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
        await message.channel.send("hii im alive!!")

bot.run(TOKEN)
