import discord
import os

from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# Connect to MongoDB
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING') # Your MongoDB connection string
client = MongoClient(MONGO_CONNECTION_STRING)  

db = client.deemos
collection = db.members  

# Iterate over all documents in the collection
for document in collection.find():
        # Extract only 'discord_name' and 'participation'
        updated_document = {
            'discord_name': document.get('discord_name', ''),
            'participation': document.get('participation', [])
        }

        # Update the document with the new structure
        collection.replace_one(
            {'_id': document['_id']},
            updated_document
        )

# Close the MongoDB connection
client.close()
