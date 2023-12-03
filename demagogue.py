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

ASPIRING_DEEMOCRAT_ROLE_ID = 1102000164601864304
DEEMOCRAT_ROLE_ID = 912034805762363473


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"An error occurred: {str(error)}")


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
        # Check if 'participation' field exists in the document
        if 'participation' in member:
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
async def check_activity(ctx):
    today_date = datetime.utcnow()

    # Define role IDs and corresponding inactivity periods
    role_inactive_periods = {
        ASPIRING_DEEMOCRAT_ROLE_ID: 1,  # Inactive for 1 month for "aspiring"
        DEEMOCRAT_ROLE_ID: 4    # Inactive for 4 months for "deemocrat"
    }

    # Define role strings
    role_strings = {
        ASPIRING_DEEMOCRAT_ROLE_ID: "aspiring deemocrat",
        DEEMOCRAT_ROLE_ID: "deemocrat"
    }

    inactive_users_list = []

    # Function to check if a user is active in the last month based on role_info
    def is_active_in_last_month(role_info):
        acquisition_date = role_info[0][2] if role_info else None

        if acquisition_date:
            acquisition_date = acquisition_date.replace(tzinfo=None)  # Remove timezone info for comparison
            return acquisition_date >= today_date - timedelta(days=30)
        else:
            return False

    # Function to check if a user is active in the last N months based on role_info
    def is_active_in_last_months(role_info, months):
        acquisition_date = role_info[1][2] if role_info else None

        if acquisition_date:
            acquisition_date = acquisition_date.replace(tzinfo=None)  # Remove timezone info for comparison
            return acquisition_date >= today_date - relativedelta(months=months)
        else:
            return False

    # Fetch all members from MongoDB
    all_members = mongo_members_collection.find()

    # Check for "aspiring" members
    for member_data in all_members:
        # Check if the member has the "aspiring deemocrat" role
        if any(role[0] == ASPIRING_DEEMOCRAT_ROLE_ID and role[1] for role in member_data.get('role_info', [])):
            # Check if the member has no entry in MongoDB or is not active in the last month
            if not is_active_in_last_month(member_data.get('role_info', [])):
                inactive_users_list.append(f"{member_data['discord_name']} ({role_strings[ASPIRING_DEEMOCRAT_ROLE_ID]})")

    # Check for "deemocrat" members
    for member_data in all_members:
        # Check if the member has the "deemocrat" role
        if any(role[0] == DEEMOCRAT_ROLE_ID and role[1] for role in member_data.get('role_info', [])):
            # Check if the member has no entry in MongoDB or is not active in the last 4 months
            if not is_active_in_last_months(member_data.get('role_info', []), role_inactive_periods[DEEMOCRAT_ROLE_ID]):
                inactive_users_list.append(f"{member_data['discord_name']} ({role_strings[DEEMOCRAT_ROLE_ID]})")

    if inactive_users_list:
        await ctx.send(f'Inactive users:\n{", ".join(inactive_users_list)}')
    else:
        await ctx.send('All users are active.')

output_channel_id = 1114195400371486840

@bot.command()
@commands.has_permissions(administrator=True)
async def update_discord_ids(ctx):
    # Get all documents in the MongoDB collection
    all_members = mongo_members_collection.find()

    for existing_member in all_members:
        discord_name = existing_member.get("discord_name")

        if discord_name:
            # Look up the discord_id in the guild
            member = discord.utils.get(ctx.guild.members, name=discord_name)

            if member:
                # Update the existing document with the discord_id
                mongo_members_collection.update_one(
                    {"discord_name": discord_name},
                    {"$set": {"discord_id": str(member.id)}}
                )
                await ctx.send(f"Updated discord_id for {discord_name} to {member.id}")
            else:
                await ctx.send(f"Member with the name {discord_name} not found in the guild.")
        else:
            await ctx.send("Discord_name is missing in a document. Skipping update.")

@bot.command()
@commands.has_permissions(administrator=True)
async def update_roles(ctx):
    # Get all documents in the MongoDB collection
    all_members = mongo_members_collection.find({"discord_id": {"$exists": True}})

    for existing_member in all_members:
        discord_id = existing_member.get("discord_id")

        if discord_id:
            # Look up the member in the guild using discord_id
            member = ctx.guild.get_member(int(discord_id))

            if member:
                # Check if the member has the specified roles
                deemocrat_role = discord.utils.get(ctx.guild.roles, id=DEEMOCRAT_ROLE_ID)
                aspiring_deemocrat_role = discord.utils.get(ctx.guild.roles, id=ASPIRING_DEEMOCRAT_ROLE_ID)

                deemocrat_status = bool(deemocrat_role in member.roles)
                aspiring_deemocrat_status = bool(aspiring_deemocrat_role in member.roles)

                # Store the role information in the MongoDB document
                role_info = [
                    (DEEMOCRAT_ROLE_ID, deemocrat_status, member.joined_at),
                    (ASPIRING_DEEMOCRAT_ROLE_ID, aspiring_deemocrat_status, member.joined_at)
                ]

                mongo_members_collection.update_one(
                    {"discord_id": discord_id},
                    {"$set": {"role_info": role_info}}
                )
                await ctx.send(f"Updated role information for {discord_id}")
            else:
                await ctx.send(f"Member with the discord_id {discord_id} not found in the guild.")
        else:
            await ctx.send("Discord_id is missing in a document. Skipping update.")


@bot.event
async def on_member_update(before, after):
    # Check if roles have been updated for the member
    if before.roles != after.roles:
        discord_id = str(after.id)

        # Check if the member is in the MongoDB collection
        existing_member = mongo_members_collection.find_one({"discord_id": discord_id})

        if existing_member:
            # Check if the specific roles exist in the guild
            deemocrat_role = discord.utils.get(after.guild.roles, id=DEEMOCRAT_ROLE_ID)
            aspiring_deemocrat_role = discord.utils.get(after.guild.roles, id=ASPIRING_DEEMOCRAT_ROLE_ID)

            if deemocrat_role and aspiring_deemocrat_role:
                # Check if the roles have changed
                role_info = existing_member.get("role_info", [])
                roles_changed = False

                # Check Deemocrat role
                deemocrat_status = bool(deemocrat_role in after.roles)
                if role_info and role_info[0][1] != deemocrat_status:
                    roles_changed = True
                role_info[0] = (DEEMOCRAT_ROLE_ID, deemocrat_status, datetime.utcnow())

                # Check Aspiring Deemocrat role
                aspiring_deemocrat_status = bool(aspiring_deemocrat_role in after.roles)
                if role_info and len(role_info) > 1 and role_info[1][1] != aspiring_deemocrat_status:
                    roles_changed = True
                role_info[1] = (ASPIRING_DEEMOCRAT_ROLE_ID, aspiring_deemocrat_status, datetime.utcnow())

                # Update the MongoDB document only if roles have changed
                if roles_changed:
                    mongo_members_collection.update_one(
                        {"discord_id": discord_id},
                        {"$set": {"role_info": role_info}}
                    )

                    # Get the specified guild and channel
                    guild = bot.get_guild(911623996682932254)  # Replace YOUR_GUILD_ID with your guild ID
                    channel = guild.get_channel(1114195400371486840)  # Replace 1114195400371486840 with your channel ID

                    # Send a message to the channel
                    await channel.send(f"Updated role information for {discord_id} ({after.name})")
        else:
            # Create a new document for the member in the MongoDB collection
            new_member = {
                "discord_id": discord_id,
                "discord_name": after.name,
                "role_info": [],
                # Add other fields as needed
            }

            # Add the new member to the MongoDB collection
            mongo_members_collection.insert_one(new_member)

            # Get the specified guild and channel
            guild = bot.get_guild(911623996682932254)  # Replace YOUR_GUILD_ID with your guild ID
            channel = guild.get_channel(output_channel_id)  # Replace 1114195400371486840 with your channel ID

            # Send a message to the channel
            await channel.send(f"Created a new document for {discord_id} ({after.name}) and updated role information.")

@bot.command()
@commands.has_permissions(administrator=True)
async def award(ctx, *args):
    participation_type = 'default_participation_type'  # Set a default participation type if none is provided

    # Check if arguments are provided
    if args:
        # If arguments are provided, assume it's the aaward functionality
        ids = args[0]
        participation_type = args[1] if len(args) > 1 else 'default_participation_type_aaward'
        
        today_date = datetime.utcnow()
        id_list = [id.strip().lower() for id in ids.split(",")]

        for discord_id in id_list:
            member = mongo_members_collection.find_one({"discord_name": discord_id})

            if member is not None:
                if 'participation' not in member:
                    member['participation'] = []

                member['participation'].append([today_date, participation_type])
                mongo_members_collection.update_one(
                    {"discord_name": discord_id},
                    {"$set": {"participation": member['participation']}}
                )
            else:
                mongo_members_collection.insert_one({
                    'discord_name': discord_id,
                    'participation': [[today_date, participation_type]],
                })

        await ctx.send("Added participation entry for specified members.")
    else:
        # If no arguments are provided, assume it's the award functionality
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
                    "participation": [(datetime.now(), participation_type)],  # List of tuples
                }
                mongo_members_collection.insert_one(new_member)
            else:
                mongo_members_collection.update_one(
                    {"discord_name": member_name},
                    {"$push": {"participation": (datetime.now(), participation_type)}}
                )

bot.run(TOKEN)
