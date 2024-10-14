from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import nest_asyncio
import asyncio
import hashlib
import hmac
import requests
import time
import logging
import uuid
import sqlite3

# Use nest_asyncio to allow nested event loops in Jupyter Notebook
nest_asyncio.apply()

BOT_TOKEN = '7580665549:AAEiILYjLzZg34wIFOBZB-FtfUhsjQMBUrA'

# Sumsub API credentials
SUMSUB_APP_TOKEN = 'prd:Fhy56fEOaBdw28xHyEbLYmX8.9jhVeXYpbDnwZyOv3MximW4RlQwbPgZ8'
SUMSUB_SECRET_KEY = 'laNtfcWcj8k1J3goskEqwnA2T6p21ydD'
SUMSUB_BASE_URL = "https://api.sumsub.com"
REQUEST_TIMEOUT = 60

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            total_credits INTEGER DEFAULT 2      
        )
    ''')
    conn.commit()
    conn.close()

# Add a new user if they don't exist in the database
def add_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id) VALUES (?)
    ''', (user_id,))
    conn.commit()
    conn.close()

# Function to check total credits
def check_credits(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT total_credits FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# Deduct a credit from the user
def deduct_credit(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET total_credits = total_credits - 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Start command handler
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    add_user(user_id)  # Add user if they don't exist
    await update.message.reply_text("You have 2 credit, which you can spend on either KYC, Full KYC, or POA.")

# Handle KYC, Full KYC, and POA requests
async def handle_message(update: Update, context: CallbackContext) -> None:
    # Ensure the bot is mentioned in the message
    if any(entity.type == 'mention' and '@sumsub_pre_bot' in update.message.text for entity in update.message.entities):
        user_id = update.message.from_user.id
        message_text = update.message.text.lower()

        add_user(user_id)  # Ensure user is in the database

        # Check total credits
        total_credits = check_credits(user_id)
        if total_credits > 0:
            if '@sumsub_pre_bot kyc' in message_text:
                websdk_link = generate_websdk_link('basic-kyc-level', str(uuid.uuid4()))
                if websdk_link:
                    await update.message.reply_text(f"Here is your KYC link: {websdk_link}")
                    deduct_credit(user_id)  # Deduct one credit
                else:
                    await update.message.reply_text("Sorry, there was an error generating your KYC link.")

            elif '@sumsub_pre_bot full_kyc' in message_text:
                websdk_link = generate_websdk_link('full-kyc-level', str(uuid.uuid4()))
                if websdk_link:
                    await update.message.reply_text(f"Here is your Full KYC link: {websdk_link}")
                    deduct_credit(user_id)  # Deduct one credit
                else:
                    await update.message.reply_text("Sorry, there was an error generating your Full KYC link.")

            elif '@sumsub_pre_bot poa' in message_text:
                websdk_link = generate_websdk_link('poa', str(uuid.uuid4()))
                if websdk_link:
                    await update.message.reply_text(f"Here is your POA link: {websdk_link}")
                    deduct_credit(user_id)  # Deduct one credit
                else:
                    await update.message.reply_text("Sorry, there was an error generating your POA link.")
            else:
                await update.message.reply_text("Invalid command. Please use '@sumsub_pre_bot kyc', '@sumsub_pre_bot full_kyc', or '@sumsub_pre_bot poa'.")
        else:
            await update.message.reply_text("You have no credits left.")

# Generate WebSDK link
def generate_websdk_link(level_name, external_user_id, ttl_in_secs=1800, lang='en'):
    url = f"{SUMSUB_BASE_URL}/resources/sdkIntegrations/levels/{level_name}/websdkLink"
    params = {
        'ttlInSecs': ttl_in_secs,
        'externalUserId': external_user_id,
        'lang': lang
    }
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    try:
        response = sign_request(requests.Request('POST', url, params=params, headers=headers, data="{}"))
        session = requests.Session()
        resp = session.send(response, timeout=REQUEST_TIMEOUT)
        logging.info(f"Generate WebSDK Link Response: {resp.status_code} - {resp.text}")
        resp.raise_for_status()
        websdk_url = resp.json().get('url')
        return websdk_url
    except Exception as e:
        logging.error(f"Error generating WebSDK link: {e}")
        return None

# Sign API request
def sign_request(request: requests.Request) -> requests.PreparedRequest:
    prepared_request = request.prepare()
    now = int(time.time())
    method = request.method.upper()
    path_url = prepared_request.path_url
    body = b'' if prepared_request.body is None else prepared_request.body
    if isinstance(body, str):
        body = body.encode('utf-8')
    data_to_sign = str(now).encode('utf-8') + method.encode('utf-8') + path_url.encode('utf-8') + body
    signature = hmac.new(
        SUMSUB_SECRET_KEY.encode('utf-8'),
        data_to_sign,
        digestmod=hashlib.sha256
    )
    prepared_request.headers['X-App-Token'] = SUMSUB_APP_TOKEN
    prepared_request.headers['X-App-Access-Ts'] = str(now)
    prepared_request.headers['X-App-Access-Sig'] = signature.hexdigest()

    logging.debug(f"Signed Request Headers: {prepared_request.headers}")
    logging.debug(f"Signed Request URL: {prepared_request.url}")
    return prepared_request

# Run the bot
async def run_bot():
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create the Application and pass the bot's token
    app = Application.builder().token(BOT_TOKEN).build()

    # Initialize the SQLite database
    init_db()

    # Command handler for /start
    app.add_handler(CommandHandler("start", start))

    # Message handler to respond when the bot is mentioned with "kyc", "full_kyc", or "poa"
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_message))

    # Initialize and start the bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Future()  # Keeps the bot running

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except RuntimeError as e:
        if str(e) == "This event loop is already running":
            loop = asyncio.get_event_loop()
            loop.create_task(run_bot())
        else:
            raise
