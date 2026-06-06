import discord
from bot import chat_bot
import asyncio
import os

TOKEN = os.getenv("BOT_TOKEN") 

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await chat_bot.register_client(client)

@client.event
async def on_message(message):
    await chat_bot.handle_message(message, bot_user=client.user)

@client.event
async def on_typing(channel, user, when):
    await chat_bot.handle_typing_start(channel, user)

async def main():
    await asyncio.gather(client.start(TOKEN), chat_bot.update()) # type: ignore
