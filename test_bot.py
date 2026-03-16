import os
import telebot

print("TEST BOT STARTED")

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("Brak TELEGRAM_TOKEN")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=["start"])
def start_cmd(message):
    print("START RECEIVED")
    bot.reply_to(message, "Start działa ✅")

@bot.message_handler(commands=["pulse"])
def pulse_cmd(message):
    print("PULSE RECEIVED")
    bot.reply_to(message, "Pulse działa ✅")

@bot.message_handler(func=lambda message: True)
def echo(message):
    print(f"MESSAGE: {message.text}")
    bot.reply_to(message, f"Odebrałem: {message.text}")

print("BEFORE POLLING")
import time

while True:
    try:
        print("START POLLING")
        bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"ERROR: {e}")
        time.sleep(5)
