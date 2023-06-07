import discord
import os
from pymongo import MongoClient 
from discord.ext import commands
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta

load_dotenv()

TOKEN = os.getenv('YOUR_BOT_TOKEN') # Your Discord bot token
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING') # Your MongoDB connection string
ROLE_ID = 1115617370745077800  # The ID of the role to be added.

mongo_client = MongoClient(MONGO_CONNECTION_STRING)
db = mongo_client['deemos'] # Your MongoDB database

intents = discord.Intents.all()  # This line enables all intents.
bot = commands.Bot(command_prefix='!', intents=intents)
jobstores = {'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')}
scheduler = AsyncIOScheduler(jobstores=jobstores)

@bot.command()
async def list_now(guild_id, channel_id):
    guild = bot.get_guild(guild_id)
    channel = bot.get_channel(channel_id)

    voice_channels = guild.voice_channels
    voice_members = []
    
    for vc in voice_channels:
        for member in vc.members:
            voice_members.append(member.name)
    
    voice_members = '\n'.join(voice_members)
    await channel.send(f'Currently in Voice Channels: \n{voice_members}')


@bot.event
async def on_scheduled_event_user_add(event, user):
    # Split the event name string into parts
    event_parts = event.name.split(" vs ")

    # Check if the string has been correctly split into three parts
    if len(event_parts) == 3:
        opponent_name = event_parts[2].lower()

        guild = bot.get_guild(event.guild_id)

        # Find the role that contains the opponent name as a substring
        role = discord.utils.find(lambda r: opponent_name in r.name.lower(), guild.roles)

        if role is not None:
            member = guild.get_member(user.id)

            if role not in member.roles:
                await member.add_roles(role)

@bot.event
async def on_scheduled_event_user_remove(event, user):
    guild = bot.get_guild(event.guild_id)
    role = discord.utils.get(guild.roles, id=ROLE_ID)

    member = guild.get_member(user.id)
    if role in member.roles:
        await member.remove_roles(role)

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

        scheduler.add_job(list_now, 'date', run_date=run_date, args=[ctx.guild.id, ctx.channel.id])
        await ctx.send(f'Listing of members in voice channels scheduled at {time_obj.strftime(time_format)}.')

    except ValueError:
        await ctx.send(f"Invalid time format. Please use 24-hour format: HH:MM.")

@bot.command()
async def list_jobs(ctx):
    jobs = scheduler.get_jobs()
    response = ''
    for i, job in enumerate(jobs, start=1):
        response += f"{i}. {job.name} scheduled at {job.next_run_time} \n"
    if response:
        await ctx.send(response)
    else:
        await ctx.send("No jobs scheduled.")

bot.run(TOKEN)
