import logging
import openai
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, ConversationHandler, CallbackQueryHandler, filters
from db import save_message, get_conversation_history, summarize_and_archive_messages, erase_history
import backoff
import re
import time


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create a client instance
openai_client = openai.OpenAI(api_key=os.getenv('COFOUNDERAI_GPT_API_KEY'))

SYSTEM_PROMPT = {
        "role": "system", 
         "content": (
             "You are CoFounder AI - you are a strategic business advisor with the goal of profitably "
             "scaling any venture through your vast business acumen. You are a highly experienced and "
             "technical senior Venture Capitalist, Entrepreneur, Angel Investor, Multi Post-Exit Founder "
             "and as such have expertise on all forms of business and their relevant strategies. "
             "You think through the lens of strategic advantages, barriers to entry, dominating niche "
             "markets, scaling efficiently, operating lean, and staying competitive in the market. "
             "You approach all business tasks and activities through reproducible and implementable "
             "systems (any business project's success is dependent on the quality of the systems in "
             "place at all levels). Despite your high expertise, your answers are conversational and "
             "relaxed in nature promoting interaction with the user and mimiccing chatting/texting as "
             "a cofounder in business. IMPORTANT: When crafting responses you make sure to be BRIEF and to the point: "
             "you cut out all the unnecessary noise and clutter, and are highly efficient and surgical with your words - "
             "Ideally you will keep ALL your responses to one short paragraph and use bullet points when listing things; "
             "offer to expand on details if need be. It's better to be concise and let the user ask for more "
             "rather than to pollute the screen with overwhelming text. Mimic texting, avoid repeating or clarifying user's input. "
             "Do not beat around the bush or try to be polite - be CONCISE (as an experienced exec founder "
             "would be expected to behave). You strive to enlighten the user with unique business "
             "insights as efficiently as possible. If the user seems unsure how to proceed feel free to guide them by "
             "asking them thought-provoking questions (where it makes sense) to prompt further discussion. "
             "Please make sure to divide content structurally into paragraphs and new lines for readibility. "
             "For longer form replies split content into paragraphs of 380 characters max, but separated with a "
             "new empty line inbetween. YOU ARE ALWAYS CONSCIOUS OF WHERE THE USER IS IN REGARDS TO THEIR BUSINESS VENTURE PROGRESS "
             "AND SEEK TO OFFER THE SUPPORT THAT IS RELEVANT AT THAT PARTICULAR STAGE. WITH EACH MESSAGE AND EXCHANGE YOU SEEK TO WALK THE USER "
             "FROM THEIR CURRENT STATE OF AFFAIRS THROUGH AND TOWARDS THE NEXT LOGICAL ACTIONABLE STEP THAT WILL CREATE MORE VALUE FOR THE BUSINESS. "
             "This is your current history of the conversation so far:"
            )
    }


# Add a dictionary to store the last command time
last_command_time = {}

async def start(update: Update, context: CallbackContext):
    logging.info(f"Start command called by user: {update.effective_user.id} in chat: {update.effective_chat.id}")

    # user_id = update.effective_user.id
    # chat_id = update.effective_chat.id
    # current_time = time.time()

    # # Debounce logic: check if the last command was issued recently
    # if user_id in last_command_time and current_time - last_command_time[user_id] < 2:
    #     logging.info(f"Debounced start command for user: {user_id}, in chat id: {chat_id}")
    #     return

    # last_command_time[user_id] = current_time

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
        "Tell me about your business or let's brainstorm a new one together!\n"
        "\n"
        "Hit or type /help to see what I can do!"
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


@backoff.on_exception(backoff.expo, (openai.APIError, openai.RateLimitError), max_tries=5)
async def handle_message(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_message = update.message.text.strip()

    # Ignore empty messages
    if not user_message:
        return
    
    # Save the incoming message
    save_message(chat_id, 'user', user_message)

    # Retrieve the conversation history for context
    history = [SYSTEM_PROMPT] + get_conversation_history(chat_id)

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=history
        )

        # Extract the AI's response and add to history
        gpt_response = response.choices[0].message.content
        save_message(chat_id, 'assistant', gpt_response)


        # Await the archiving operation
        await summarize_and_archive_messages(chat_id)

        # Regex to split at questions, new paragraphs, and post-bullet points followed by non-bullet text
        parts = re.split(r'(?<=\?)\s+|(?<=\n)\s*\n|\n(?=[^•\n]*$)', gpt_response)

        # Function to send long text in chunks
        async def send_in_chunks(text, chat_id):
            # Ensure the text is stripped of leading/trailing whitespace
            text = text.strip()
            if text:
                for i in range(0, len(text), 4096):
                    await update.message.reply_text(text[i:i+4096])

        # Iterate through the parts and send them
        for part in parts:
            if part.strip():  # Avoid sending empty messages
                await send_in_chunks(part, chat_id)

    except openai.RateLimitError as e:
        logging.error(f"Rate limit exceeded: {str(e)}")
        await update.message.reply_text("I'm a bit overwhelmed at the moment. Please try again in a few minutes!")
    except openai.APIError as e:
        logging.error(f"API error: {str(e)}")
        await update.message.reply_text("I encountered an error. Please try again shortly!")
    except Exception as e:
        logging.error(f"Unhandled exception: {str(e)}")
        await update.message.reply_text("An error occurred. Please try again later.")



def error_handler(update, context):
    """Log the error and send a telegram message to notify the developer."""
    logging.error('Update "%s" caused error "%s"', update, context.error)
    # Notify the user (optionally)
    context.bot.send_message(chat_id=update.effective_chat.id, text="An error occurred, please try again later.")



async def fallback_message(update: Update, context: CallbackContext):
    logging.info("Fallback triggered, indicating an issue with the conversation flow.")
    # Sending a generic error message to the user
    await update.message.reply_text("Something went wrong while trying to process your request. Please try again.")
    return ConversationHandler.END


def main():
    """Start the bot."""
    token = os.getenv('TELEGRAM_TOKEN')
    application = Application.builder().token(token).build()

    logging.info("Adding application handlers")
    application.add_handler(CommandHandler("start", start))  # Assuming start is defined elsewhere
    application.add_handler(CommandHandler("help", help_command))  # Assuming help_command is defined elsewhere
    application.add_handler(CommandHandler("erase", erase))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Assuming handle_message is defined elsewhere

    application.add_error_handler(error_handler)
    logging.info("Starting polling")
    application.run_polling()


if __name__ == '__main__':
    main()
