import os
import openai
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Set your OpenAI and Telegram API keys as environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI API
openai.api_key = OPENAI_API_KEY

# Define a function to call the LLM API for translation using completions.create
def translate_text(input_text):
    try:
        # Using the new 'completions.create' method in OpenAI v1.0.0+
        response = openai.completions.create(
            model="gpt-4",  # Adjust model to your subscription, gpt-4 or gpt-3.5
            prompt=f"Translate the following text to English: {input_text}",
            max_tokens=100,
            temperature=0.5
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# Define the start command
def start(update: Update, context) -> None:
    update.message.reply_text('Hi! Send me any text, and I will translate it to English!')

# Handle incoming messages
def handle_message(update: Update, context) -> None:
    user_message = update.message.text
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