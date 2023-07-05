import os
import time
import json
import requests
import schedule
import calendar
from pymongo import MongoClient
from dateutil.relativedelta import relativedelta
import logging
import discord
import os 
from discord.ext import commands
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta

load_dotenv()

TOKEN = os.getenv('YOUR_BOT_TOKEN') # Your Discord bot token
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING') # Your MongoDB connection string
ROLE_ID = 1115617370745077800  # The ID of the role to be added.

client = MongoClient(MONGO_CONNECTION_STRING)  # Connect to your MongoDB
db = client.deemos 
vip = db.vip

intents = discord.Intents.all()  # This line enables all intents.
bot = commands.Bot(command_prefix='!', intents=intents)
jobstores = {'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')}
scheduler = AsyncIOScheduler(jobstores=jobstores)



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
async def list_now(ctx):
    guild = ctx.guild

    voice_channels = guild.voice_channels
    voice_members = []
    
    for vc in voice_channels:
        for member in vc.members:
            voice_members.append(member.name)
    
    voice_members = '\n'.join(voice_members)
    await ctx.send(f'Currently in Voice Channels: \n{voice_members}')

from datetime import datetime

@bot.command()
@commands.has_permissions(administrator=True)  # Ensure only admins can run this command
async def award(ctx, participation_type: str):
    guild = ctx.guild

    voice_channels = guild.voice_channels
    voice_members = []
    
    for vc in voice_channels:
        for member in vc.members:
            voice_members.append(member.name)
    
    voice_members = '\n'.join(voice_members)
    await ctx.send(f'Currently in Voice Channels: \n{voice_members}')

    # MongoDB interaction starts here
    for member_name in voice_members.split("\n"):
        # Look for documents that have the same discord_id
        existing_member = vip.find_one({"$or": [{"discord_id": member_name}, {"name": member_name}]})


        if existing_member is None: 
            # If no document is found, create a new document
            new_member = {
                "discord_id": member_name,
                "name": "",
                "minutes_today": 0,
                "pending_award": False,
                "steam_id_64": "",
                "participation": [[datetime.now(), participation_type]],
                "geforce_now": False,
                "level": "none",
                "vip_this_month": False
            }
            vip.insert_one(new_member)
        else:
            # If the member already exists, add the participation_type to their document
            vip.update_one(
                {"discord_id": member_name},
                {"$push": {"participation": [datetime.now(), participation_type]}}
            )

@bot.command()
async def steam(ctx, steam_id: str):
    # Check if Steam ID is valid (consists only of digits)
    if not steam_id.isdigit():
        await ctx.send('Invalid Steam ID. Please provide a valid ID.')
        return

    # Fetch the member's document from the MongoDB collection
    existing_member = vip.find_one({'discord_id': str(ctx.message.author.id)})

    # If the member doesn't exist in the database, create a new document for them
    if existing_member is None:
        new_member = {
            'discord_id': str(ctx.message.author.id),
            'name': ctx.message.author.name,
            'steam_id_64': steam_id,
            'minutes_today': 0,
            'pending_award': False,
            'participation': [],
            'geforce_now': False,
            'level': 'none',
            'vip_this_month': False
        }
        vip.insert_one(new_member)
        await ctx.send('Your Steam ID has been registered!')
    else:
        # If the member exists, update their Steam ID
        vip.update_one(
            {'discord_id': str(ctx.message.author.id)},
            {'$set': {'steam_id_64': steam_id}}
        )
        await ctx.send('Your Steam ID has been updated!')


@bot.command()
@commands.has_permissions(administrator=True)  # Ensure only admins can run this command
async def rank(ctx):
    # Fetch all members from the MongoDB collection
    all_members = vip.find()

    # Create a list of tuples containing member name and participation count
    participation_counts = [(member['discord_id'], len(member['participation'])) for member in all_members if len(member['participation']) > 0]

    # Sort the list by participation count in descending order
    participation_counts.sort(key=lambda x: x[1], reverse=True)

    # Convert the list into a string for sending
    ranking_message = '\n'.join(f'{name}: {count}' for name, count in participation_counts)

    await ctx.send(f'Participation ranking:\n{ranking_message}')

from datetime import datetime

@bot.command()
@commands.has_permissions(administrator=True)  # Ensure only admins can run this command
async def aaward(ctx, ids: str):
    today_date = datetime.utcnow()

    # Split the string into individual IDs
    id_list = [id.strip().lower() for id in ids.split(",")]

    for discord_id in id_list:
        member = vip.find_one({"discord_id": discord_id})

        if member is not None:
            # Append new participation entry
            member['participation'].append([today_date, "training"])

            # Update member document in database
            vip.update_one({"discord_id": discord_id}, {"$set": {"participation": member['participation']}})
        else:
            # Create a new document
            vip.insert_one({
                'discord_id': discord_id,
                'minutes_today': 0,
                'pending_award': False,
                'steam_id_64': "",
                'participation': [[today_date, "training"]],  # add the participation today
                'geforce_now': False,
                'level': 'recruit',
                'vip_this_month': False,
            })
        
    await ctx.send("Added participation entry for specified members.")


bot.run(TOKEN)
