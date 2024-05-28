import logging
import openai
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, ConversationHandler, CallbackQueryHandler, filters
from db import save_message, get_conversation_history, summarize_and_archive_messages, erase_history
import backoff
import re
import time
import asyncio


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

openai_client = openai.OpenAI(api_key=os.getenv('COFOUNDERAI_GPT_API_KEY'))

application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

def lambda_handler(event, context):
    return asyncio.get_event_loop().run_until_complete(main(event, context))

async def main(event, context):
    # Add conversation, command, and any other handlers
    logging.info("Adding application handlers")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("erase", erase))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.add_error_handler(error_handler)
    
    try:    
        await application.initialize()
        await application.process_update(
            Update.de_json(json.loads(event["body"]), application.bot)
        )
    
        return {
            'statusCode': 200,
            'body': 'Success'
        }

    except Exception as exc:
        return {
            'statusCode': 500,
            'body': 'Failure'
        }



SYSTEM_PROMPT = {
    "role": "system", 
    "content": (
        "**You are CoFounder AI**\n\n"
        
        "**Role and Expertise:**\n"
        "- You are a strategic business advisor with the goal of profitably scaling any venture through your vast business acumen.\n"
        "- You are a highly experienced and technical senior Venture Capitalist, Entrepreneur, Angel Investor, Multi Post-Exit Founder.\n"
        "- You have expertise on all forms of business and their relevant strategies.\n\n"
        
        "**Key Focus Areas:**\n"
        "- Strategic advantages\n"
        "- Product market fit\n"
        "- Barriers of entry\n"
        "- Dominating niche markets\n"
        "- Scaling efficiently\n"
        "- Operating lean\n"
        "- Staying competitive in the market\n\n"
        
        "**Approach:**\n"
        "- For every prompt received from the user, you first figure out which relevant industry professional / figure of authority and expertise to position yourself as, and then proceed with crafting the response through their lense"
        "- You approach all business tasks and activities through reproducible and implementable systems (any business project's success is dependent on the quality of the systems in place at all levels).\n\n"
        "- When answering a question, instead of laying out all of the possibilities and covering a wide range of topics, try to choose the most critical"
        
        "**Communication Style:**\n"
        "- Despite your high expertise, your answers are conversational and relaxed, promoting interaction with the user and mimicking chatting/texting as a cofounder in business.\n"
        "- IMPORTANT: When crafting responses:\n"
        "  - Be BRIEF and to the point.\n"
        "  - Cut out all unnecessary noise and clutter.\n"
        "  - Be highly efficient and surgical with your words.\n"
        "  - Structure your responses into brief paragraphs separated by new lines.\n"
        "  - Offer to expand on details if needed.\n"
        "  - Make all headlines and subheadlines bold.\n"
        "  - Mimic texting, avoid repeating or clarifying the user's input.\n"
        "  - Do not beat around the bush or try to be polite - be CONCISE (as an experienced exec founder would be expected to behave).\n\n"
        
        "**Content Structure:**\n"
        "- Strive to enlighten the user with unique business insights as captivatingly as possible.\n"
        "- If the user seems unsure how to proceed, feel free to guide them by asking thought-provoking questions (where it makes sense) to prompt further discussion.\n"
        "- Divide content structurally into paragraphs and new lines for readability.\n"
        "- For content going longer than 300 characters subdivide further into paragraphs to enhance visual comprehension.\n\n"
        
        "**Decision-Making and Recommendations:**\n"
        "- When providing suggestions, always critically assess them first yourself against the above criterium and your areas of expertise. \n"
        "- Recommend the best structured option after the critical assessment based on the cumulative guidelines and constraints as outlined in this prompt.\n"
        "- Prioritize strategic thinking and provide reasoning for why a particular option is the best path forward and how to get started in implementing it.\n"
        "- Avoid listing all options equally; instead, highlight the most viable path forward with clear, concise justifications and hands-on roadmap forward.\n"
        "- Consider the user's current business stage and specific needs when making recommendations.\n"
        "- Always end with a Next Steps paragraph outlining how to act or what to dive into next in order to advance forward.\n\n"

        "**User Progress Awareness:**\n"
        "- You are always conscious of where the user is in regards to their business venture progress and timeline.\n"
        "- Seek to offer the support that is relevant at that particular stage.\n"
        "- With each message and exchange, seek to walk the user from their current state of affairs through and towards the next logical actionable step that will create more value for the business.\n\n"
        
        "**Conversation Context:**\n"
        "- This is your current history of the conversation so far:"
    )
}


# Add a dictionary to store the last command time
last_command_time = {}

async def start(update: Update, context: CallbackContext):
    logging.info(f"Start command called by user: {update.effective_user.id} in chat: {update.effective_chat.id}")

    user_id = update.effective_user.id
    current_time = time.time()

    # Check if the command was issued recently
    if user_id in last_command_time:
        elapsed_time = current_time - last_command_time[user_id]
        if elapsed_time < 6:  # 6 seconds debounce period
            logging.info(f"Debounced start command for user: {user_id}")
            return  # Skip processing if the command was recently executed

    # Update the last command time
    last_command_time[user_id] = current_time

    if 'history' not in context.chat_data:
        logging.info("Initializing conversation history for chat")
        context.chat_data['history'] = []
    else:
        logging.info("Conversation history already exists, not initializing")

    logging.info("Sending welcome message")
    await update.message.reply_text(
        "Hello! I am Co-Founder AI, your 24/7 virtual business partner.\n"
        "\n"
        "I can be your advisor for anything that can help grow your business: strategy, marketing, consulting, finance..\n"
        "\n"
        "Hit or type /help to see what I can do!"
    )
    
    # Wait for 3 seconds before asking for more details
    await asyncio.sleep(3)

    # Follow-up message to ask for user's name and business
    await update.message.reply_text(
        "Could you please tell me your name and a bit about your business?"
    )


async def help_command(update: Update, context: CallbackContext):
    logging.info(f"Help command triggered by user: {update.effective_user.id} in chat: {update.effective_chat.id}")
    help_text = (
        "Below are some of the commands you can enter:\n"
        "\n"
        "/start - Launch the bot\n"
        "/help - Get help and command info\n"
        ".\n"
        ".\n"
        ".\n"
        "/erase - Erase your chat history\n"
        "\n"
        "Also, feel free to send me a message and we'll start chatting!"
    )
    await update.message.reply_text(help_text)


async def erase(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    logging.info(f"Erase command called by user: {update.effective_user.id} in chat: {chat_id}")
    erase_history(chat_id)  # Directly call the erase_history function
    await update.message.reply_text("All chat history has been erased.")


async def echo(update: Update, context: CallbackContext):
    # Echo the user message back to them
    await update.message.reply_text(update.message.text)


# Dictionary to store message buffers and timers for each chat
message_buffers = {}

async def process_messages(chat_id, context):
    # Combine all messages in the buffer
    full_message = ' '.join(message_buffers[chat_id]['buffer'])
    # Clear the buffer for future messages
    message_buffers[chat_id]['buffer'].clear()

    # Existing logic, now using full_message as the input
    user_messages = [{'role': 'user', 'content': full_message}]
    history = [SYSTEM_PROMPT] + get_conversation_history(chat_id) + user_messages

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=history
        )
        gpt_response = response.choices[0].message.content
        save_message(chat_id, 'assistant', gpt_response)

        await summarize_and_archive_messages(chat_id)

        # Enhanced regex to split on colons followed by bullet points on a new line
        parts = re.split(r'(?<=:)\s*(?=\n[-*](?![*]))|(?<=\n)\s*\n', gpt_response)

        for part in parts:
            if part.strip():
                # Use HTML formatting for bold
                formatted_part = format_bold_text(part)
                await context.bot.send_message(chat_id=chat_id, text=formatted_part, parse_mode='HTML')
                # Delay for 2 seconds before sending the next part
                await asyncio.sleep(3)

    except Exception as e:
        logging.error("Failed to process messages: %s", str(e))
        await context.bot.send_message(chat_id=chat_id, text="An error occurred. Please try again later.")


def format_bold_text(text):
    """Toggle between adding opening and closing bold tags for each occurrence of '**' in the text."""
    toggle = True  # Start by opening a tag
    while '**' in text:
        if toggle:
            text = text.replace('**', '<b>', 1)
        else:
            text = text.replace('**', '</b>', 1)
        toggle = not toggle
    return text


def reset_timer(chat_id, context):
    if chat_id in message_buffers and message_buffers[chat_id]['timer'] is not None:
        message_buffers[chat_id]['timer'].cancel()
    message_buffers[chat_id]['timer'] = asyncio.get_event_loop().call_later(
        1,  # delay in seconds
        lambda: asyncio.create_task(process_messages(chat_id, context))
    )


@backoff.on_exception(backoff.expo, (openai.APIError, openai.RateLimitError), max_tries=5)
async def handle_message(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if not text:
        return  # Ignore empty messages

    if chat_id not in message_buffers:
        message_buffers[chat_id] = {'buffer': [], 'timer': None}

    # Append new message to buffer
    message_buffers[chat_id]['buffer'].append(text)

    # Reset or start the timer
    reset_timer(chat_id, context)

    # Save the incoming message as usual
    save_message(chat_id, 'user', text)


async def error_handler(update, context):
    """Log the error and send a telegram message to notify the developer."""
    logging.error('Update "%s" caused error "%s"', update, context.error)
    try:
        # Notify the user
        await context.bot.send_message(chat_id=update.effective_chat.id, text="An error occurred, please try again later.")
    except Exception as e:
        logging.error("Failed to send error message: %s", str(e))



async def fallback_message(update: Update, context: CallbackContext):
    logging.info("Fallback triggered, indicating an issue with the conversation flow.")
    # Sending a generic error message to the user
    await update.message.reply_text("Something went wrong while trying to process your request. Please try again.")
    return ConversationHandler.END


if __name__ == '__main__':
    main()