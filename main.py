import os
import telebot

print("BOT STARTING...")

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("Brak TELEGRAM_TOKEN")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda message: True)
def all_messages(message):
    print(f"GOT MESSAGE: {message.text}")
    bot.reply_to(message, f"Odebrałem: {message.text}")

print("BOT STARTED")
bot.infinity_polling()
