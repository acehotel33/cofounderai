# Telegram AI CoFounder Bot

Welcome to the Telegram AI CoFounder Bot repository! This bot serves as a virtual business partner, providing strategic advice and insights to help entrepreneurs grow their businesses effectively.

## Overview

The Telegram AI CoFounder Bot utilizes OpenAI's GPT-3.5-turbo model to engage users in business discussions, answer queries, and offer actionable advice. It is designed to be user-friendly, responsive, and efficient in helping users navigate their entrepreneurial journeys.

## Features

- **Business Advisory**: Offers insights on strategy, marketing, consulting, and finance.
- **Conversational Interface**: Engages users in a natural, conversational manner.
- **Message History Management**: Stores and archives conversations for future reference.
- **Error Handling**: Robust error management to ensure a smooth user experience.
- **Customizable System Prompts**: Tailors responses based on the context of the conversation.

## Requirements

- Python 3.7 or higher
- MongoDB (for storing conversation history)
- OpenAI API key
- Telegram Bot Token

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/acehotel33/cofounderai 
   ```
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Set up your environment variables:

* COFOUNDERAI_GPT_API_KEY: Your OpenAI API key.
* TELEGRAM_TOKEN: Your Telegram bot token.
* COFOUNDERAI_MONGO_URI: Your MongoDB connection URI.

4. Run the bot:
   ```
   python main.py
   ```

## Usage
Start a conversation with the bot using the /start command.
Use the /help command to see available commands.
The bot will guide you through a series of questions to understand your business needs better.

## Commands
/start: Launch the bot and initiate conversation.
/help: List available commands.
/erase: Erase your chat history.

## Code Structure
* main.py: Contains the main bot logic, handlers, and conversation management.
* db.py: Handles MongoDB interactions for storing and retrieving chat history.

## Contributing
Contributions are welcome! If you have suggestions for improvements or features, please open an issue or submit a pull request.
