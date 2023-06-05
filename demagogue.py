import discord
import os
from pymongo import MongoClient 
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv('YOUR_BOT_TOKEN') # Your Discord bot token
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING') # Your MongoDB connection string

mongo_client = MongoClient(MONGO_CONNECTION_STRING)
db = mongo_client['deemos'] # Your MongoDB database

intents = discord.Intents.all()  # This line enables all intents.
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"An error occurred: {str(error)}")

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

@bot.event
async def on_raw_reaction_add(payload):
    # Ensure the reaction is what you expect
    if str(payload.emoji) != 'reaction_emoji': # the reaction emoji to trigger sign-up
        return

    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return

    message = await channel.fetch_message(payload.message_id)
    if message is None or message.author != bot.user:
        return

    event_doc = db.events.find_one({"message_id": str(payload.message_id)})
    if event_doc is None:
        return

    user_id = payload.user_id
    if user_id not in event_doc['users']:
        # Add user to the event
        db.events.update_one({"message_id": str(payload.message_id)}, {"$push": {"users": user_id}})

        # Update the message to reflect new user
        users_str = ', '.join([f'<@{user}>' for user in event_doc['users']])
        await message.edit(content=f'Users signed up for this event: {users_str}')

@bot.command()
async def list_voice_members(ctx):
    guild = ctx.guild
    voice_channels = guild.voice_channels

    voice_members = []
    
    for vc in voice_channels:
        for member in vc.members:
            voice_members.append(member.name)
            voice_members.append('\n')
    
    voice_members = ', '.join(voice_members)
    await ctx.send(f'Currently in Voice Channels: \n{voice_members}')

bot.run(TOKEN)
