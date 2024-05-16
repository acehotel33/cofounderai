from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError
import openai
import os
import asyncio
from openai import AsyncOpenAI 
from datetime import datetime, timezone
import logging
from motor.motor_asyncio import AsyncIOMotorClient



# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

openai_client = AsyncOpenAI(api_key=os.getenv('COFOUNDERAI_GPT_API_KEY'))

# Initialize MongoDB client
MONGO_URI = os.getenv('COFOUNDERAI_MONGO_URI')
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.ChatHistory  
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
    """Retrieve the conversation history for a given chat, including archived messages."""
    try:
        conversation = conversations.find_one({"chat_id": chat_id}, {"_id": 0, "messages": 1, "archived_messages": 1})
        if not conversation:
            return []

        # Combine messages and archived_messages
        history = []
        if 'archived_messages' in conversation and conversation['archived_messages']:
            # Adding archived messages as system messages for context
            for archive in conversation['archived_messages']:
                history.append({"role": "system", "content": archive})

        if 'messages' in conversation and conversation['messages']:
            history.extend([{"role": msg['role'], "content": msg['content']} for msg in conversation['messages']])
        
        return history
    except PyMongoError as e:
        logging.error(f"MongoDB error: {str(e)}")
        return []  # Return an empty list in case of error




async def summarize_and_archive_messages(chat_id):
    """Retrieve, summarize, and archive old messages asynchronously using OpenAI."""
    conversation = conversations.find_one({"chat_id": chat_id})
    if conversation and len(conversation['messages']) > 25:
        # Retrieve messages to be summarized and any existing summary.
        messages_to_summarize = conversation['messages'][:25]
        existing_summary = conversation['archived_messages'][0] if 'archived_messages' in conversation and conversation['archived_messages'] else ""

        # Combine existing summary with new messages for a comprehensive summary.
        context = existing_summary + "\n" + "\n".join([msg['content'] for msg in messages_to_summarize])

        messages_formatted = [{"role": "system", "content": "You are an archiving bot tasked with summarizing, condensing, and archiving conversation history. Please make sure to compactly pack as much contextual info as possible into your summary (using bullet points and dictionaries) so that your counterparty AI bot can later reference the 'memory' you create in order to always be up-to-date on the context of the whole conversation. The conversation will be predominantly based around business and ventures so please help your AI bot pal in retaining this memory. Most importantly, make sure you summarize the content and not continue the conversation."}] + \
                             [{"role": "user", "content": context}]

        try:
            # Asynchronous call to OpenAI's API for summarization
            response = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages_formatted
            )
            updated_summary = response.choices[0].message.content

            # Ensure there is only one archived entry and it's updated, not added to
            conversations.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {
                        "archived_messages": [updated_summary],
                        "messages": conversation['messages'][25:]  # retain only the unsummarized messages
                    }
                }
            )
        except Exception as e:
            logging.error(f"OpenAI API error: {str(e)}")


async def erase_history(chat_id):
    """Erase the chat history by moving all messages to an erased history archive asynchronously."""
    try:
        logging.info(f"Attempting to fetch conversation for chat_id: {chat_id}")
        # Asynchronously fetch the current state of the conversation
        conversation = await conversations.find_one({"chat_id": chat_id})
        logging.info(f"Conversation fetched for chat_id: {chat_id}, data: {conversation}")

        # Handle the case where there is no existing conversation
        if not conversation:
            logging.info(f"No conversation found for chat_id: {chat_id}. No action taken.")
            return  # Exit as there's nothing to erase

        existing_messages = conversation.get('messages', [])
        existing_archived = conversation.get('archived_messages', [])

        # Check if there are any messages or archived messages to process
        if not existing_messages and not existing_archived:
            logging.info(f"No messages or archived messages to erase for chat_id: {chat_id}. No action taken.")
            return  # Exit if there's nothing to erase

        # Compile all current messages and archives into a single entry
        all_content = {
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "messages": existing_messages,
            "archived_messages": existing_archived
        }

        # Only update the database if there is content to archive
        if existing_messages or existing_archived:
            logging.info(f"Updating database to erase history for chat_id: {chat_id}")
            update_result = await conversations.update_one(
                {"chat_id": chat_id},
                {
                    "$push": {"erased_messages": all_content},
                    "$set": {"messages": [], "archived_messages": []}
                }
            )
            if update_result.modified_count == 0:
                logging.info("No changes made to the database for chat_id: {}".format(chat_id))
            else:
                logging.info("Successfully erased history for chat_id: {}".format(chat_id))
        else:
            logging.info("No messages or archives to process for chat_id: {}".format(chat_id))

    except Exception as e:  # Using a broader exception to catch all potential async errors
        logging.error("Failed to erase history for chat_id: {}. Error: {}".format(chat_id, str(e)))
        raise  # Optional: re-raise the exception if you want to handle it further up the call stack

