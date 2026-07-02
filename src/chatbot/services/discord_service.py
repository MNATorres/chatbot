import discord
import os
from loguru import logger

async def send_discord_message(channel_id: int, text: str):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    try:
        await client.login(os.getenv("DISCORD_TOKEN"))
        channel = await client.fetch_channel(channel_id)
        await channel.send(text)
        return True
    except Exception:
        logger.exception("Error en Discord")
        return False
    finally:
        await client.close()

async def fetch_channel_history(channel_id: int, limit: int = 10):
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    
    try:
        await client.login(os.getenv("DISCORD_TOKEN"))
        channel = await client.fetch_channel(channel_id)
        messages = []
        async for msg in channel.history(limit=limit):
            messages.append(f"{msg.author.name}: {msg.content}")
        return messages
    except Exception:
        logger.exception("Error fetching Discord history")
        return []
    finally:
        await client.close()

async def fetch_all_channels():
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    try:
        await client.login(os.getenv("DISCORD_TOKEN"))
        channels_info = []
        async for guild in client.fetch_guilds(limit=150):
            channels = await guild.fetch_channels()
            for ch in channels:
                if isinstance(ch, discord.TextChannel):
                    channels_info.append(f"Server: {guild.name} | Channel: {ch.name} | ID: {ch.id}")
        return channels_info
    except Exception:
        logger.exception("Error fetching all channels")
        return []
    finally:
        await client.close()