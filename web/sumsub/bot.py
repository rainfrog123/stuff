from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import asyncio
import hashlib
import hmac
import requests
import time
import logging
import uuid
import os

# Replace with your bot token
BOT_TOKEN = '7580665549:AAEiILYjLzZg34wIFOBZB-FtfUhsjQMBUrA'
# Replace with your group chat ID (use a negative number for groups)
GROUP_CHAT_ID = -1001983252802

# Sumsub API credentials
SUMSUB_APP_TOKEN = "prd:WOCxi7YZ65cLyCJqRNS69i5d.5umRA9KrRyyM5N8GNj6IeJuwQ0xKiOF0"  # Replace with your actual secret key
SUMSUB_SECRET_KEY = "bOcz37g6kKp6RTAf3mObbJkqSRrELvu3"  # Replace with your actual app token
SUMSUB_BASE_URL = "https://api.sumsub.com"  # Make sure to use https and correct URL (sandbox or production)
REQUEST_TIMEOUT = 60

async def start(update: Update, context: CallbackContext) -> None:
    if update.message:
        user_id = update.message.from_user.id
        chat_member = await context.bot.get_chat_member(GROUP_CHAT_ID, user_id)

        if chat_member.status in ['member', 'administrator', 'creator']:
            await update.message.reply_text("Welcome, you are a member of the group!")
        else:
            await update.message.reply_text("Sorry, this bot is only for members of the group.")

async def handle_message(update: Update, context: CallbackContext) -> None:
    if update.message and update.message.from_user:
        user_id = update.message.from_user.id
        chat_member = await context.bot.get_chat_member(GROUP_CHAT_ID, user_id)

        if chat_member.status in ['member', 'administrator', 'creator']:
            message_text = update.message.text.lower()

            if '@sumsub_pre_bot kyc' in message_text:
                websdk_link = generate_websdk_link('basic-kyc-level', str(uuid.uuid4()))
                if websdk_link:
                    await update.message.reply_text(f"Here is your KYC link: {websdk_link}")
                else:
                    await update.message.reply_text("Sorry, there was an error generating your KYC link.")
            
            elif '@sumsub_pre_bot poa' in message_text:
                websdk_link = generate_websdk_link('POA', str(uuid.uuid4()))
                if websdk_link:
                    await update.message.reply_text(f"Here is your POA link: {websdk_link}")
                else:
                    await update.message.reply_text("Sorry, there was an error generating your POA link.")

            elif '@sumsub_pre_bot' in message_text:
                await update.message.reply_text("I'm sorry, I don't understand that command. Please use '@sumsub_pre_bot kyc' or '@sumsub_pre_bot poa'.")
        else:
            await update.message.reply_text("Sorry, this bot is only for members of the group.")

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

def sign_request(request: requests.Request) -> requests.PreparedRequest:
    prepared_request = request.prepare()
    now = int(time.time())
    method = request.method.upper()
    path_url = prepared_request.path_url
    body = b'' if prepared_request.body is None else prekpared_request.body
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

async def run_bot():
    logging.basicConfig(level=logging.INFO)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_message))

    await app.initialize()
    await app.start()
    try:
        await app.updater.start_polling()  # Starts the polling process
        await asyncio.Future()  # Keeps the bot running
    finally:
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except RuntimeError as e:
        if str(e) == "This event loop is already running":
            loop = asyncio.get_event_loop()
            loop.create_task(run_bot())
        else:
            raise
