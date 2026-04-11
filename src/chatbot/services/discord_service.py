import discord
import os

async def send_discord_message(channel_id: int, text: str):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    try:
        await client.login(os.getenv("DISCORD_TOKEN"))
        channel = await client.fetch_channel(channel_id)
        await channel.send(text)
        return True
    except Exception as e:
        print(f"Error en Discord: {e}")
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
    except Exception as e:
        print(f"Error fetching Discord history: {e}")
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
    except Exception as e:
        print(f"Error fetching all channels: {e}")
        return []
    finally:
        await client.close()