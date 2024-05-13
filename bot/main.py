import logging
import os
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Hello! I am Co-Founder AI, your virtual business partner.\nI am currently in development. Use /help to see what I can do!')

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text('/start - Launch the bot\n/help - Get help and command info')

async def echo(update: Update, context: CallbackContext):
    # Echo the user message back to them
    await update.message.reply_text(update.message.text)

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    token = os.getenv('TELEGRAM_TOKEN')
    bot = Bot(token)

    # Create the Application using the bot
    application = Application.builder().token(token).build()

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()