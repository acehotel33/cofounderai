from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError
import openai
import os
import asyncio
from openai import AsyncOpenAI 
from datetime import datetime, timezone
import logging

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

openai_client = AsyncOpenAI(api_key=os.getenv('COFOUNDERAI_GPT_API_KEY'))

# Initialize MongoDB client
MONGO_URI = os.getenv('COFOUNDERAI_MONGO_URI')
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.ChatHistory  # Change 'your_database_name' to your actual database name
conversations = db.conversations  # Assume a collection named 'conversations'

current_utc_time = datetime.now(timezone.utc)


def save_message(chat_id, role, content):
    """Save a message to the database."""
    try:
        conversations.update_one(
            {"chat_id": chat_id},
            {"$push": {"messages": {
                "role": role, 
                "content": content, 
                "timestamp": datetime.now(timezone.utc).isoformat()  # Convert datetime to ISO format string
            }}},
            upsert=True
        )
    except PyMongoError as e:
        logging.error(f"MongoDB error: {str(e)}")


def get_conversation_history(chat_id):
    """Retrieve the conversation history for a given chat and prepare it for JSON serialization."""
    try:
        conversation = conversations.find_one({"chat_id": chat_id}, {"_id": 0, "messages": 1})
        if conversation and 'messages' in conversation:
            # Ensure all timestamps are in string format
            for message in conversation['messages']:
                if 'timestamp' in message and isinstance(message['timestamp'], datetime):
                    message['timestamp'] = message['timestamp'].isoformat()
        return conversation['messages'] if conversation else []
    except PyMongoError as e:
        logging.error(f"MongoDB error: {str(e)}")
        return []  # Return an empty list in case of error




async def summarize_and_archive_messages(chat_id):
    """Retrieve, summarize, and archive old messages asynchronously using OpenAI."""
    conversation = conversations.find_one({"chat_id": chat_id})
    if conversation and len(conversation['messages']) > 20:
        # Retrieve messages to be summarized
        messages_to_summarize = conversation['messages'][:10]
        messages_formatted = [{"role": "system", "content": "Summarize the following business conversation:"}] + \
                             [{"role": "user", "content": msg['content']} for msg in messages_to_summarize]

        try:
            # Asynchronous call to OpenAI's API for summarization
            response = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages_formatted
            )
            summary = response.choices[0].message.content

            # Update the database to archive messages and store summary
            conversations.update_one(
                {"chat_id": chat_id},
                {
                    "$push": {"archived_messages": {"$each": [summary], "$position": 0}},
                    "$set": {"messages": conversation['messages'][10:]}
                }
            )
        except Exception as e:
            logging.error(f"OpenAI API error: {str(e)}")



