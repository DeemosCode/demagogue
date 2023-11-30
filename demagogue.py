#     demagogue
#     Copyright (C) 2023 Nikolaos Katzakis

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.


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

TOKEN = os.getenv('YOUR_BOT_TOKEN') 
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING') 
ROLE_ID = 1115617370745077800  

client = MongoClient(MONGO_CONNECTION_STRING)  
db = client.deemos 
mongo_members_collection = db.members

intents = discord.Intents.all() 
bot = commands.Bot(command_prefix='!', intents=intents)
jobstores = {'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')}
scheduler = AsyncIOScheduler(jobstores=jobstores)


@bot.event
async def on_scheduled_event_user_add(event, user):
    event_parts = event.name.split(" vs ")

    if len(event_parts) == 3:
        opponent_name = event_parts[2].lower()

        guild = bot.get_guild(event.guild_id)
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

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"An error occurred: {str(error)}")

@bot.command()
async def lookup(ctx, *, member: commands.MemberConverter):
    await ctx.send(f'Member ID: {member.id}\nMember Name: {member.name}')

@bot.command()
async def migrate(ctx):
    guild = discord.utils.get(bot.guilds, id=911623996682932254)  # Replace with your guild ID

    aspiring_deemocrat_role = discord.utils.get(guild.roles, id=1102000164601864304)
    deemocrat_role = discord.utils.get(guild.roles, id=912034805762363473)

    for member in guild.members:
        if aspiring_deemocrat_role in member.roles:
            # vip.insert_one({'discord_name': member.id, 'nickname': member.nick, 'rank': 'recruit'})
            
            print(member)
    
    # for member in guild.members:
    #     if deemocrat_role in member.roles:
    #         # vip.insert_one({'discord_name': member.id, 'nickname': member.nick, 'rank': 'deemocrat'})
    #         print(member.id)


    # print('Members with aspiring deemocrat role have been added to the MongoDB collection')


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


@bot.command()
@commands.has_permissions(administrator=True)
async def award(ctx, participation_type: str):
    guild = ctx.guild

    voice_channels = guild.voice_channels
    voice_members = []
    
    for vc in voice_channels:
        for member in vc.members:
            voice_members.append(member.name.lower())  # convert to lowercase here
    
    voice_members = '\n'.join(voice_members)
    await ctx.send(f'Currently in Voice Channels: \n{voice_members}')

    for member_name in voice_members.split("\n"):
        existing_member = mongo_members_collection.find_one({"discord_name": member_name})

        if existing_member is None: 
            new_member = {
                "discord_name": member_name,
                "name": "",
                "minutes_today": 0,
                "pending_award": False,
                "steam_id_64": "",
                "participation": [[datetime.now(), participation_type]],
                "geforce_now": False,
                "level": "none",
                "vip_this_month": False
            }
            mongo_members_collection.insert_one(new_member)
        else:
            mongo_members_collection.update_one(
                {"discord_name": member_name},
                {"$push": {"participation": [datetime.now(), participation_type]}}
            )


@bot.command()
async def steam(ctx, steam_id: str):
    if not steam_id.isdigit():
        await ctx.send('Invalid Steam ID. Please provide a valid ID.')
        return

    discord_id_lower = str(ctx.message.author.id).lower() # convert to lowercase here
    existing_member = mongo_members_collection.find_one({'discord_name': discord_id_lower})

    if existing_member is None:
        new_member = {
            'discord_name': discord_id_lower,
            'name': ctx.message.author.name,
            'steam_id_64': steam_id,
            'minutes_today': 0,
            'pending_award': False,
            'participation': [],
            'geforce_now': False,
            'level': 'none',
            'vip_this_month': False
        }
        mongo_members_collection.insert_one(new_member)
        await ctx.send('Your Steam ID has been registered!')
    else:
        mongo_members_collection.update_one(
            {'discord_name': discord_id_lower},
            {'$set': {'steam_id_64': steam_id}}
        )
        await ctx.send('Your Steam ID has been updated!')


@bot.command()
@commands.has_permissions(administrator=True)  
async def rank(ctx):
    all_members = mongo_members_collection.find()

    participation_counts = [(member['discord_name'], len(member['participation'])) for member in all_members if len(member['participation']) > 0]

    participation_counts.sort(key=lambda x: x[1], reverse=True)

    ranking_message = '\n'.join(f'{name}: {count}' for name, count in participation_counts)

    await ctx.send(f'Participation ranking:\n{ranking_message}')

@bot.command()
@commands.has_permissions(administrator=True)  
async def rankmonth(ctx, month_name: str):
    # Convert the month name to its corresponding number
    try:
        month_number = datetime.strptime(month_name, "%B").month
    except ValueError:
        await ctx.send("Invalid month name. Please provide a valid month (e.g., 'January', 'February', etc.).")
        return

    all_members = mongo_members_collection.find()

    participation_counts = []

    current_year = datetime.utcnow().year

    for member in all_members:
        month_participation = [entry for entry in member['participation'] if entry[0].month == month_number and entry[0].year == current_year]
        if len(month_participation) > 0:
            participation_counts.append((member['discord_name'], len(month_participation)))

    participation_counts.sort(key=lambda x: x[1], reverse=True)

    ranking_message = '\n'.join(f'{name}: {count}' for name, count in participation_counts)

    await ctx.send(f'Participation ranking for {month_name} {current_year}:\n{ranking_message}')


@bot.command()
@commands.has_permissions(administrator=True)  
async def rank30(ctx):
    all_members = mongo_members_collection.find()

    participation_counts = []

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    for member in all_members:
        recent_participation = [entry for entry in member['participation'] if entry[0] >= thirty_days_ago]
        if len(recent_participation) > 0:
            participation_counts.append((member['discord_name'], len(recent_participation)))

    participation_counts.sort(key=lambda x: x[1], reverse=True)

    ranking_message = '\n'.join(f'{name}: {count}' for name, count in participation_counts)

    await ctx.send(f'Participation ranking (last 30 days):\n{ranking_message}')


@bot.command()
@commands.has_permissions(administrator=True)  
async def countrank(ctx):
    all_members = mongo_members_collection.find()

    participation_counts = []
    for member in all_members:
        if len(member['participation']) > 0:
            type_counts = {}
            for item in member['participation']:
                if item[1] in type_counts:
                    type_counts[item[1]] += 1
                else:
                    type_counts[item[1]] = 1
            participation_counts.append((member['discord_name'], len(member['participation']), type_counts))

    participation_counts.sort(key=lambda x: x[1], reverse=True)

    ranking_message = '\n'.join(f'{count} \t{name},\t\t\t{types}' for name, count, types in participation_counts)

    await ctx.send(f'Participation ranking:\n{ranking_message}')


@bot.command()
@commands.has_permissions(administrator=True)  
async def aaward(ctx, ids: str, parttype: str):
    today_date = datetime.utcnow()
    id_list = [id.strip().lower() for id in ids.split(",")]

    for discord_id in id_list:
        member = mongo_members_collection.find_one({"discord_name": discord_id})

        if member is not None:
            member['participation'].append([today_date, parttype])
            mongo_members_collection.update_one({"discord_name": discord_id}, {"$set": {"participation": member['participation']}})
        else:
            mongo_members_collection.insert_one({
                'discord_name': discord_id,
                'minutes_today': 0,
                'pending_award': False,
                'steam_id_64': "",
                'participation': [[today_date, "training"]],
                'geforce_now': False,
                'level': 'recruit',
                'vip_this_month': False,
            })
        
    await ctx.send("Added participation entry for specified members.")

@bot.command()
async def request(ctx):
    if not isinstance(ctx.channel, discord.DMChannel):  # Ensure the command is run in a private message
        return

    guild = discord.utils.get(bot.guilds, id=911623996682932254)  # Replace with your guild ID

    voice_channels = guild.voice_channels
    voice_members = []

    for vc in voice_channels:
        for member in vc.members:
            voice_members.append(str(member.id).lower())  # convert to lowercase here

    for member_id in voice_members:
        member = mongo_members_collection.find_one({"discord_name": member_id})

        if member is not None:
            member['participation'].append([datetime.now(), 'random'])
            mongo_members_collection.update_one({"discord_name": member_id}, {"$set": {"participation": member['participation']}})
        else:
            mongo_members_collection.insert_one({
                'discord_name': member_id,
                'minutes_today': 0,
                'pending_award': False,
                'steam_id_64': "",
                'participation': [[datetime.now(), 'random']],
                'geforce_now': False,
                'level': 'none',
                'vip_this_month': False,
            })
        
    await ctx.send("Added 'random' participation for members in voice channels.")

@bot.command()
async def check_activity(ctx):
    today_date = datetime.utcnow()

    # Define role IDs and corresponding inactivity periods
    role_inactive_periods = {
        1102000164601864304: 1,  # Inactive for 1 month for "aspiring"
        912034805762363473: 4    # Inactive for 4 months for "deemocrat"
    }

    # Define role strings
    role_strings = {
        1102000164601864304: "aspiring deemocrat",
        912034805762363473: "deemocrat"
    }

    inactive_users_list = []

    # Function to check if a user is active in the last month
    def is_active_in_last_month(user_data):
        last_participation_dates = [entry[0] for entry in user_data.get('participation', []) if entry[0] >= today_date - timedelta(days=30) and entry[0] <= today_date]
        
        if last_participation_dates:
            most_recent_participation_date = max(last_participation_dates)
            return most_recent_participation_date >= today_date - timedelta(days=30)
        else:
            return False

    # Function to check if a user is active in the last N months
    def is_active_in_last_months(user_data, months):
        last_participation_date = max(entry[0] for entry in user_data.get('participation', [])) if user_data.get('participation') else None
        return last_participation_date is not None and last_participation_date >= today_date - relativedelta(months=months)

    # Fetch guild members with either of the specified roles
    aspiring_members = [member for member in ctx.guild.members if discord.utils.get(member.roles, id=1102000164601864304)]
    deemocrat_members = [member for member in ctx.guild.members if discord.utils.get(member.roles, id=912034805762363473)]

    # Check for "aspiring" members
    for member in aspiring_members:
        # Get the user data from MongoDB based on discord_name
        user_data = mongo_members_collection.find_one({"discord_name": member.name})

        # Check if the member joined the guild less than 30 days ago
        join_date = user_data.get('join_date', None)
        if join_date is not None:
            join_date = datetime.strptime(join_date, "%Y-%m-%d %H:%M:%S")
            if (today_date - join_date).days < 30:
                continue  # Skip this member, as they are not considered inactive

        # Check if the member has no entry in MongoDB or no participation entries in the last month
        if user_data is None or not is_active_in_last_month(user_data):
            inactive_users_list.append(f"{member.name} ({role_strings[1102000164601864304]})")

    # Check for "deemocrat" members
    for member in deemocrat_members:
        # Get the user data from MongoDB based on discord_name
        user_data = mongo_members_collection.find_one({"discord_name": member.name})

        # Check if the member joined the guild less than 30 days ago
        join_date = user_data.get('join_date', None)
        if join_date is not None:
            join_date = datetime.strptime(join_date, "%Y-%m-%d %H:%M:%S")
            if (today_date - join_date).days < 30:
                continue  # Skip this member, as they are not considered inactive

        # Check if the member has no entry in MongoDB or no participation entries in the last 4 months
        if user_data is None or not is_active_in_last_months(user_data, role_inactive_periods[912034805762363473]):
            inactive_users_list.append(f"{member.name} ({role_strings[912034805762363473]})")

    if inactive_users_list:
        await ctx.send(f'Inactive users:\n{", ".join(inactive_users_list)}')
    else:
        await ctx.send('All users are active.')

output_channel_id = 1114195400371486840

@bot.event
async def on_member_update(before, after):
    roles_to_track = ["deemocrat", "aspiring deemocrat"]
    
    role_changes = set(after.roles) - set(before.roles)

    roles_data = []
    for role in roles_to_track:
        has_role = role in after.roles
        roles_data.append({
            "role": role,
            "hasRole": has_role,
            "timestamp": datetime.utcnow() if has_role else None
        })

    member_data = {
        "discord_id": str(after.id),
        "discord_name": after.display_name,
        "roles": roles_data
    }

    # Upsert the member data into the MongoDB collection
    mongo_members_collection.update_one(
        {"discord_id": str(after.id)},
        {"$set": member_data},
        upsert=True
    )

     # Get the channel by ID
    channel = bot.get_channel(output_channel_id)

    # Send the output to the specified channel
    await channel.send(f"Role update logged in MongoDB for {after.display_name}")

bot.run(TOKEN)
