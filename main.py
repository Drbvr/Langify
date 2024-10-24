import os
from openai import AsyncOpenAI
import asyncio
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Set your OpenAI and Telegram API keys as environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize the new OpenAI API client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Define an asynchronous function to call the new OpenAI API for translation
async def async_translate_text(input_text):
    try:
        # Asynchronous request to OpenAI ChatCompletion API using the new interface
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",  # Or use gpt-4 if your subscription supports it
            messages=[
                {"role": "user", "content": input_text}
            ]
        )

        # Extracting the message content using the correct attribute
        translated_message = response.choices[0].message.content.strip()
        return translated_message
    except Exception as e:
        return f"Error: {str(e)}"

# Synchronous wrapper to call the async function using asyncio.run()
def translate_text(input_text):
    return asyncio.run(async_translate_text(input_text))

# Define the start command
def start(update: Update, context) -> None:
    update.message.reply_text('Hi! Send me any text, and I will translate it to English!')

# Handle incoming messages
def handle_message(update: Update, context) -> None:
    user_message = update.message.text
    # Call the synchronous wrapper that runs the async translation
    translated_message = translate_text(user_message)
    update.message.reply_text(translated_message)

def main():
    # Set up the Updater with the bot token
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add command handler for '/start'
    dp.add_handler(CommandHandler("start", start))

    # Add a message handler to handle incoming messages
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Start the bot
    updater.start_polling()

    # Run the bot until Ctrl-C is pressed
    updater.idle()

if __name__ == '__main__':
    main()