import discord
import os
from pymongo import MongoClient 
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
import schedule
import time
import requests
import schedule
import calendar
from dateutil.relativedelta import relativedelta
import logging
from systemd import journal
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv('YOUR_BOT_TOKEN') # Your Discord bot token
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING') # Your MongoDB connection string
ROLE_ID = 1115617370745077800  # The ID of the role to be added.
SESSION_ID = os.getenv('SESSIONID', '0')

log = logging.getLogger('demagogue')
log.addHandler(journal.JournaldLogHandler())
log.setLevel(logging.INFO)

mongo_client = MongoClient(MONGO_CONNECTION_STRING)
db = mongo_client.deemos 
vip = db.vip  # Access the 'vip' collection

# Set interval
INTERVAL_IN_MINUTES = 1
MINUTES_REQUIREMENT_IF_SUCCESS = 15
MINUTES_REQUIREMENT_IF_FAILURE = 120
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1119199023602073610/nmqzDMXyWjPI0GLd5x-U4QPLbLHVCd17ecHAkQKs0JzBVeZcfPqlMeRkdLSsLH-HpDrG"
WAR='war'
TRAINING='training'
SEED='seed'
MISC='misc'
cookies = {'sessionid': SESSION_ID}

intents = discord.Intents.all()  # This line enables all intents.
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command()
@commands.has_permissions(administrator=True)  # Ensure only admins can run this command
async def list_voice_now(ctx):
    guild = ctx.guild
    voice_channels = guild.voice_channels

    voice_members = []
    
    for vc in voice_channels:
        for member in vc.members:
            voice_members.append(member.name)
    
    voice_members = '\n'.join(voice_members)
    await ctx.send(f'Currently in Voice Channels:\n {voice_members}')


# @bot.event
# async def on_scheduled_event_user_add(event, user):
#     # Split the event name string into parts
#     event_parts = event.name.split(" vs ")

#     # Check if the string has been correctly split into three parts
#     if len(event_parts) == 3:
#         opponent_name = event_parts[2].lower()

#         guild = bot.get_guild(event.guild_id)

#         # Find the role that contains the opponent name as a substring
#         role = discord.utils.find(lambda r: opponent_name in r.name.lower(), guild.roles)

#         if role is not None:
#             member = guild.get_member(user.id)

#             if role not in member.roles:
#                 await member.add_roles(role)

# @bot.event
# async def on_scheduled_event_user_remove(event, user):
# # Split the event name string into parts
#     event_parts = event.name.split(" vs ")

#     # Check if the string has been correctly split into three parts
#     if len(event_parts) == 3:
#         opponent_name = event_parts[2].lower()

#         guild = bot.get_guild(event.guild_id)

#         # Find the role that contains the opponent name as a substring
#         role = discord.utils.find(lambda r: opponent_name in r.name.lower(), guild.roles)

#     member = guild.get_member(user.id)
#     if role in member.roles:
#         await member.remove_roles(role)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"An error occurred: {str(error)}")


# @bot.command()
# @commands.has_permissions(administrator=True)  # Ensure only admins can run this command
# async def strip(ctx):
#     guild = ctx.guild  # The guild (server) from the current context

#     deemocrat = discord.utils.get(guild.roles, id=aspiring_deemocrat_role_id)
#     aspiring = discord.utils.get(guild.roles, id=deemocrat_role_id)

#     for member in guild.members:
#         print(f"{member} removed")
#         if deemocrat in member.roles:
#             await member.remove_roles(deemocrat)
#             print("deemocrat")

#         if aspiring in member.roles:
#             await member.remove_roles(aspiring)
#             print("aspiring deemocrat")
            
# @bot.command()
# @commands.has_permissions(administrator=True)  # Ensure only admins can run this command
# async def list_aspiring_deemocrats(ctx):
#     guild = ctx.guild
#     aspiring_deemocrat_role = discord.utils.get(guild.roles, id=aspiring_deemocrat_role_id) # Get the aspiring_deemocrat role

#     aspiring_deemocrats = []

#     for member in guild.members:
#         if aspiring_deemocrat_role in member.roles:  # Check if the member has the aspiring_deemocrat role
#             aspiring_deemocrats.append(member.name)

#     aspiring_deemocrats = '\n'.join(aspiring_deemocrats)
#     await ctx.send(f'Aspiring Deemocrats:\n {aspiring_deemocrats}')



def post_to_discord(content):
    data = {"content": content}
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)

    if response.status_code != 204:
        print(f"Failed to send message to Discord: {response.text}")

def count_days_of_type(type,player_document):
    return sum(1 for rec in player_document['participation'] if rec[1] == type and rec[0].month == current_month and rec[0].year == current_year)

def calculate_expiration_date(player_doc):
    # Fetch the participation records
    participation_records = player_doc['participation']

    # Fetch dates from participation records for 'seed' type in the current calendar month
    current_year = datetime.utcnow().year
    current_month = datetime.utcnow().month
    dates_seeded_successfully = [datetime.fromisoformat(rec[0]) for rec in participation_records if rec[1] == "seed" and datetime.fromisoformat(rec[0]).year == current_year and datetime.fromisoformat(rec[0]).month == current_month]

    # Count successful days in current calendar month
    successful_days_current_month = len(dates_seeded_successfully)

    # Initializing variable
    has_vip_until_end_of_month = False

    if successful_days_current_month >= 7:
        # If player has been successful for 7 or more days this month, set expiration to the end of the current month
        last_day_of_month = calendar.monthrange(current_year, current_month)[1]  # Get the last day of the current month
        expiration_date = datetime(current_year, current_month, last_day_of_month, 23, 59, 59).isoformat()  # Set the expiration to the end of the current month
        has_vip_until_end_of_month = True
    else:
        # Otherwise, set expiration to 24 hours in the future
        expiration_timestamp = time.time() + (24 * 60 * 60)
        expiration_date = datetime.utcfromtimestamp(expiration_timestamp).isoformat()

    return (expiration_date, has_vip_until_end_of_month)

def check_and_promote_deemocrat():
    # Fetch all players
    all_players = vip.find({})
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    
    # Iterate through all players and perform tasks
    for player in all_players:
        steam_id_64 = player['steam_id_64']

        # Count days player played war or training in current calendar month
        days_played_war_this_month = count_days_of_type(player,WAR)
        days_played_training_this_month = count_days_of_type(player,TRAINING)

        # If player played war or training 3 or more days this month, set level to 'deemocrat'
        if (days_played_war_this_month + days_played_training_this_month) >= 3:
            vip.update_one(
                {'steam_id_64': steam_id_64},
                {
                    '$set': {'level': 'deemocrat'}  # Set 'level' to 'deemocrat'
                }
            )
            print(f"PROMOTION TO DEEMOCRAT for {player['name']}")
            post_to_discord(f"PROMOTION TO DEEMOCRAT for {player['name']}")

    print("Checked for deemocrat promotions")

def award_vip(steam_id_64, player_name):
    # Fetch the document for this player
    player_doc = vip.find_one({'steam_id_64': steam_id_64})
    
    # calculate how until when the VIP will be valid
    date_calc_result = calculate_expiration_date(player_doc)
    has_vip_this_month = date_calc_result[1]
    expiration_date = date_calc_result[0]

    # If today's date is already in dates_seeded_successfully, return early
    if datetime.utcnow().date() in count_days_of_type(player_doc,SEED):
        return

    # parameters for http request
    # check cookies
    params = {'steam_id_64': steam_id_64, 'name': player_name, 'expiration': expiration_date}
    
    # try to make the api call    
    try:
        response = requests.get('http://server.deemos.club/api/do_add_vip', cookies=cookies, params=params)
        response.raise_for_status()
        vip.update_one(
            {'steam_id_64': steam_id_64},
            {
                '$set': {'pending_award': False}, # reset 'pending_award'
                '$push': {'participation': [datetime.utcnow().isoformat(), SEED]}  # Add the current date and time to 'participation' with 'seed' as participation type
            }
        )
        print(f"VIP Awarded to {steam_id_64} {player_name}")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred while adding VIP status: {err}")
        # save it to try again later
        vip.update_one(
            {'steam_id_64': steam_id_64},
            {
                '$set': {'pending_award': True}, # Set 'pending_award' to true
            }
        )

def award_pending():
     # Check for players with pending_award: true and make API call for each
    pending_award_players = vip.find({'pending_award': True})
    for player in pending_award_players:
        steam_id_64 = player['steam_id_64']
        player_name = player['name']
        award_vip(steam_id_64,player_name)

def reset_minutes_today():
    all_players = vip.find({})
    for player in all_players:
        steam_id_64 = player['steam_id_64']
        vip.update_one(
            {'steam_id_64': steam_id_64},
            {
                '$set': {'minutes_today': 0}  # Reset 'minutes_today' to 0
            }
        )
    print("Reset minutes_today for all players")

def job():
    no_of_players=0
    cookies = {'sessionid': SESSION_ID}
        
    try:
        response = requests.get('http://server.deemos.club/api/get_players_fast', cookies=cookies)
        response.raise_for_status()  # Raise an exception if the response was unsuccessful
    except requests.exceptions.RequestException as err:
        log.info ("An error occurred: ", err)
    else:
        data = response.json()
        no_of_players= len(data['result'])
        if data['failed'] != False:
            print(f'Error in API response: {data}')
        else:
            for player in data['result']:
                steam_id_64 = player['steam_id_64']
                player_name = player['name']

                # Find the document for this player
                doc = vip.find_one({'steam_id_64': steam_id_64})

                if doc:
                    # Convert dates_seeded_successfully to dates only (no time) for comparison
                    dates_seeded_successfully_only = count_days_of_type(doc,SEED)

                    # If today's date is already in dates_seeded_successfully, return early
                    if datetime.utcnow().date() in dates_seeded_successfully_only:
                        return
                    # add minutes to that player
                    vip.update_one(
                        {'steam_id_64': steam_id_64},
                        {'$inc': {'minutes_today': INTERVAL_IN_MINUTES}}  # Increment the 'minutes_today' field by interval
                    )
                    doc = vip.find_one({'steam_id_64': steam_id_64})  # Fetch the document again to get updated 'minutes_today'
                else:
                    # Create a new document for this player
                    vip.insert_one({
                        'discord_id': '',
                        'name': player_name,
                        'minutes_today': INTERVAL_IN_MINUTES,
                        'pending_award': False,
                        'steam_id_64': steam_id_64,
                        'participation': [],
                        'geforce_now': False,
                        'level': 'recruit',
                        'vip_this_month':False,
                    })
                    doc = vip.find_one({'steam_id_64': steam_id_64})  # Fetch the document to use below

                # Check award condition
                if (no_of_players >= 50 and doc['minutes_today'] >= MINUTES_REQUIREMENT_IF_SUCCESS) or (doc['minutes_today'] >= MINUTES_REQUIREMENT_IF_FAILURE):

                    # Make external API call
                    award_vip(steam_id_64,player_name)


    print(f"Ran job - No of players : {no_of_players}")    

schedule.every(INTERVAL_IN_MINUTES).minutes.do(job)
schedule.every(1).hours.do(check_and_promote_deemocrat)
schedule.every().day.at("07:00").do(reset_minutes_today)  # Reset 'minutes_today' to 0 every day at 7AM

bot.run(TOKEN)

while True:
    schedule.run_pending()
    time.sleep(1)
