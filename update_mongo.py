import discord
import os

from pymongo import MongoClient

# Connect to MongoDB
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING') # Your MongoDB connection string
client = MongoClient(MONGO_CONNECTION_STRING)  

db = client.deemos  # Replace with your database name
collection = db.members  # Replace with your collection name

# Iterate over all documents in the collection
for document in collection.find():
    # Get the values of member_id and member_name
    discord_id = document.get('discord_id')

    # Update the document with the new field
    collection.update_one(
        {"_id": document["_id"]},  # Assuming each document has an "_id" field
        {"$set": {"discord_name": discord_id}, "$unset": {"discord_id": ""}}
    )

# Close the MongoDB connection
client.close()
