import os
from openai import AsyncOpenAI
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
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
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a translator that translates any input to English."},
                {"role": "user", "content": input_text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error during OpenAI API call: {e}")
        return "An error occurred while processing your request. Please try again later."

# Synchronous wrapper to call the async function using asyncio.run()
def translate_text(input_text):
    return asyncio.run(async_translate_text(input_text))

# Define the start command
def start(update: Update, context) -> None:
    user_id = update.effective_user.id
    logging.info(f"User {user_id} started the bot.")

    # Check if user is approved
    if not is_user_approved(user_id):
        if is_admin(user_id):
            logging.info("Admin is using the bot and is already approved.")
            update.message.reply_text("Hi! Send me any text, and I will translate it to English!")
        else:
            logging.info(f"User {user_id} is not approved and is requesting approval.")
            update.message.reply_text("You are not authorized to use this bot. Please wait for approval.")
            request_approval(update, context)
    else:
        logging.info(f"User {user_id} is approved.")
        update.message.reply_text("Hi! Send me any text, and I will translate it to English!")

# Check if a user is the admin
def is_admin(user_id):
    return str(user_id) == db["bot_data"].get("admin_id")

# Check if a user is approved
def is_user_approved(user_id):
    try:
        approved = "approved_users" in db["bot_data"] and str(user_id) in db["bot_data"]["approved_users"]
        logging.info(f"User {user_id} approval status: {'approved' if approved else 'not approved'}")
        return approved
    except Exception as e:
        logging.error(f"Error checking user approval status: {e}")
        return False

# Request approval for a new user
def request_approval(update: Update, context) -> None:
    user_id = update.effective_user.id
    if is_user_approved(user_id) or is_admin(user_id):
        logging.info(f"User {user_id} is already approved or is the admin, skipping approval request.")
        return

    logging.info(f"Requesting approval for new user: {user_id}")

    # Create inline keyboard with "Approve" and "Deny" buttons
    keyboard = [
        [
            InlineKeyboardButton("Approve", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("Deny", callback_data=f"deny_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the approval request to the admin with inline buttons
    context.bot.send_message(
        chat_id=ADMIN_TELEGRAM_ID,
        text=f"New user detected: {user_id}\n\nDo you want to approve or deny access?",
        reply_markup=reply_markup
    )

# Handle the admin's response to approval requests
def handle_approval_response(update: Update, context) -> None:
    query = update.callback_query
    query.answer()

    # Extract the action (approve/deny) and user_id from the callback data
    action, user_id = query.data.split("_")

    if action == "approve":
        try:
            if "approved_users" not in db["bot_data"]:
                db["bot_data"]["approved_users"] = []
            db["bot_data"]["approved_users"].append(str(user_id))
            context.bot.send_message(chat_id=user_id, text="You have been approved! You can now use the bot.")
            query.edit_message_text(text=f"User {user_id} approved.")
        except Exception as e:
            logging.error(f"Error approving user {user_id}: {e}")
            query.edit_message_text(text="An error occurred while approving the user.")
    elif action == "deny":
        try:
            context.bot.send_message(chat_id=user_id, text="You have been denied access to this bot.")
            query.edit_message_text(text=f"User {user_id} denied.")
        except Exception as e:
            logging.error(f"Error denying user {user_id}: {e}")
            query.edit_message_text(text="An error occurred while denying the user.")

# Handle incoming messages
def handle_message(update: Update, context) -> None:
    user_id = update.effective_user.id
    user_message = update.message.text
    logging.info(f"handle_message triggered for User {user_id} with message: {user_message}")

    # Check if the user is banned
    if "banned_users" in db["bot_data"] and str(user_id) in db["bot_data"]["banned_users"]:
        logging.info(f"User {user_id} is banned. Ignoring message.")
        update.message.reply_text("You are banned from using this bot.")
        return

    # Check if the user is approved
    if not is_user_approved(user_id):
        if is_admin(user_id):
            logging.info(f"Admin {user_id} is recognized as approved.")
        else:
            logging.info(f"User {user_id} is not approved, requesting             approval.")
            update.message.reply_text("You are not authorized to use this bot. Please wait for approval.")
            request_approval(update, context)
            return

    # Translate message for approved users
    try:
        translated_message = translate_text(user_message)
        logging.info(f"Translated message for user {user_id}: {translated_message}")
        update.message.reply_text(translated_message)
    except Exception as e:
        logging.error(f"Error translating message for user {user_id}: {e}")
        update.message.reply_text("An error occurred while translating your message. Please try again later.")

def main():
    # Set up the Updater with the bot token
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    # Set the admin ID if not already set in the database
    if "bot_data" not in db:
        db["bot_data"] = {}
    if "admin_id" not in db["bot_data"]:
        db["bot_data"]["admin_id"] = ADMIN_TELEGRAM_ID

    # Add the admin to the approved users list if not already present
    if "approved_users" not in db["bot_data"]:
        db["bot_data"]["approved_users"] = []
    if ADMIN_TELEGRAM_ID not in db["bot_data"]["approved_users"]:
        db["bot_data"]["approved_users"].append(ADMIN_TELEGRAM_ID)
        logging.info(f"Admin {ADMIN_TELEGRAM_ID} added to approved users.")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add command handler for '/start'
    dp.add_handler(CommandHandler("start", start))

    # Add a message handler to handle incoming messages
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Add a callback query handler for inline keyboard approval actions
    dp.add_handler(CallbackQueryHandler(handle_approval_response))

    # Start the bot
    updater.start_polling()

    # Run the bot until Ctrl-C is pressed
    updater.idle()

if __name__ == '__main__':
    main()