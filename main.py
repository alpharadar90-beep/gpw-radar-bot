import os
import telebot

print("BOT STARTING...")

TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise RuntimeError("Brak TELEGRAM_TOKEN")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "Bot działa ✅")

@bot.message_handler(commands=['pulse'])
def pulse_cmd(message):
    bot.reply_to(message, "Pulse działa ✅")

print("BOT STARTED")
bot.infinity_polling(skip_pending=True)
