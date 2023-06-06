import discord
import os
from pymongo import MongoClient 
from discord.ext import commands
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

load_dotenv()
TOKEN = os.getenv('YOUR_BOT_TOKEN') # Your Discord bot token
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING') # Your MongoDB connection string

mongo_client = MongoClient(MONGO_CONNECTION_STRING)
db = mongo_client['deemos'] # Your MongoDB database

intents = discord.Intents.all()  # This line enables all intents.
bot = commands.Bot(command_prefix='!', intents=intents)
scheduler = AsyncIOScheduler()

async def list_members(guild, channel):
    voice_channels = guild.voice_channels
    voice_members = []
    
    for vc in voice_channels:
        for member in vc.members:
            voice_members.append(member.name)
    
    voice_members = '\n'.join(voice_members)
    await channel.send(f'Currently in Voice Channels: \n{voice_members}')


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    scheduler.start()

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"An error occurred: {str(error)}")

@bot.command()
async def list(ctx, time: str):
    time_format = "%H:%M"
    try:
        time_obj = datetime.strptime(time, time_format).time()
        current_time = datetime.now().time()
        if current_time > time_obj:
            await ctx.send(f"The time specified has already passed for today.")
            return

        run_date = datetime.now().replace(hour=time_obj.hour, minute=time_obj.minute, second=time_obj.second)

        scheduler.add_job(list_members, 'date', run_date=run_date, args=[ctx.guild, ctx.channel])
        await ctx.send(f'Listing of members in voice channels scheduled at {time_obj.strftime(time_format)}.')

    except ValueError:
        await ctx.send(f"Invalid time format. Please use 24-hour format: HH:MM.")

bot.run(TOKEN)
