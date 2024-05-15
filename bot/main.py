import logging
import openai
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
from db import save_message, get_conversation_history, summarize_and_archive_messages, erase_history
import backoff


# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Create a client instance
openai_client = openai.OpenAI(api_key=os.getenv('COFOUNDERAI_GPT_API_KEY'))

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Hello! I am Co-Founder AI, your virtual business partner.\nI am currently in development. Use /help to see what I can do!')
    context.chat_data['history'] = []  # Initialize conversation history

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text('/start - Launch the bot\n/help - Get help and command info')

async def echo(update: Update, context: CallbackContext):
    # Echo the user message back to them
    await update.message.reply_text(update.message.text)

@backoff.on_exception(backoff.expo, (openai.APIError, openai.RateLimitError), max_tries=5)
async def handle_message(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_message = update.message.text

    # Save the incoming message
    save_message(chat_id, 'user', user_message)

    # Retrieve the conversation history for context
    history = get_conversation_history(chat_id)


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

        # Check if the response is too long and split it if necessary
        max_length = 4096
        if len(gpt_response) > max_length:
            parts = [gpt_response[i:i+max_length] for i in range(0, len(gpt_response), max_length)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(gpt_response)
    except openai.RateLimitError as e:
        logging.error(f"Rate limit exceeded: {str(e)}")
        await update.message.reply_text("I'm a bit overwhelmed at the moment. Please try again in a few minutes!")
    except openai.APIError as e:
        logging.error(f"API error: {str(e)}")
        await update.message.reply_text("I encountered an error. Please try again later.")
    except Exception as e:
        logging.error(f"Unhandled exception: {str(e)}")
        await update.message.reply_text("An error occurred. Please try again later.")


def erase_command(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    erase_history(chat_id)  # Call the function to erase history
    update.message.reply_text("Your chat history has been successfully erased.")


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    token = os.getenv('TELEGRAM_TOKEN')

    # Create the Application using the bot
    application = Application.builder().token(token).build()

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("erase", erase_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
