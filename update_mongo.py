import discord
import os

from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# Connect to MongoDB
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING') # Your MongoDB connection string
client = MongoClient(MONGO_CONNECTION_STRING)  

db = client.deemos  # Replace with your database name
collection = db.members  # Replace with your collection name

for document in collection.find():
    # Check if the document has the 'participation' field
    if 'participation' in document:
        # Convert the participation array
        new_participation = [
            (entry[0], entry[1])
            for entry in document['participation']
        ]

        # Update the document with the new structure
        collection.update_one(
            {'_id': document['_id']},
            {'$set': {'participation': new_participation}}
        )

# Close the MongoDB connection
client.close()
