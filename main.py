import os
from openai import AsyncOpenAI
import asyncio
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from replit import db
import logging

# Set your OpenAI and Telegram API keys as environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")

# Initialize the new OpenAI API client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define an asynchronous function to call the OpenAI API for translation
async def async_translate_text(input_text):
    try:
        # Asynchronous request to OpenAI ChatCompletion API using the new interface
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",  # Or use gpt-4 if your subscription supports it
            messages=[
                {"role": "system", "content": "You are a translator that translates any input to English."},
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
    user_id = update.effective_user.id
    logging.info(f"User {user_id} started the bot.")
    update.message.reply_text('Hi! Send me any text, and I will translate it to English!')

# Check if a user is the admin
def is_admin(user_id):
    return user_id == db["bot_data"].get("admin_id")

# Handle "/set_data" command for the admin
def handle_set_data(update: Update, context) -> None:
    user_id = update.effective_user.id
    user_message = update.message.text
    parts = user_message.split()

    if len(parts) >= 3:
        key = parts[1]
        value = " ".join(parts[2:])  # Handle multi-word values

        # Ensure user data exists
        if "users" not in db["bot_data"]:
            db["bot_data"]["users"] = {}
        if str(user_id) not in db["bot_data"]["users"]:
            db["bot_data"]["users"][str(user_id)] = {}

        db["bot_data"]["users"][str(user_id)][key] = value
        update.message.reply_text(f"Data '{key}' set to '{value}' for user {user_id}")
    else:
        update.message.reply_text("Usage: /set_data [key] [value]")

# Handle "/get_data" command for the admin
def handle_get_data(update: Update, context) -> None:
    user_id = update.effective_user.id
    user_message = update.message.text
    parts = user_message.split()

    if len(parts) == 2:
        key = parts[1]
        value = db["bot_data"]["users"].get(str(user_id), {}).get(key, "Not found")
        update.message.reply_text(f"Data for '{key}' is '{value}' for user {user_id}")
    else:
        update.message.reply_text("Usage: /get_data [key]")

# Handle "/ban_user" command for the admin
def handle_ban_user(update: Update, context) -> None:
    parts = update.message.text.split()
    if len(parts) == 2:
        user_id_to_ban = parts[1]
        if "banned_users" not in db["bot_data"]:
            db["bot_data"]["banned_users"] = []
        db["bot_data"]["banned_users"].append(user_id_to_ban)
        update.message.reply_text(f"User {user_id_to_ban} has been banned.")
    else:
        update.message.reply_text("Usage: /ban_user [user_id]")

# Handle incoming messages
def handle_message(update: Update, context) -> None:
    user_id = update.effective_user.id
    user_message = update.message.text
    logging.info(f"User {user_id} sent message: {user_message}")

    # Check if user is banned
    if "banned_users" in db["bot_data"] and str(user_id) in db["bot_data"]["banned_users"]:
        update.message.reply_text("You are banned from using this bot.")
        return

    # Check for admin commands
    if is_admin(user_id):
        if user_message.startswith("/set_data"):
            handle_set_data(update, context)
        elif user_message.startswith("/get_data"):
            handle_get_data(update, context)
        elif user_message.startswith("/ban_user"):
            handle_ban_user(update, context)
        return

    # Otherwise, handle normal user message
    translated_message = translate_text(user_message)
    update.message.reply_text(translated_message)

def main():
    # Set up the Updater with the bot token
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    # Set the admin ID if not already set in the database
    if "bot_data" not in db:
        db["bot_data"] = {}
    if "admin_id" not in db["bot_data"]:
        db["bot_data"]["admin_id"] = ADMIN_TELEGRAM_ID 

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