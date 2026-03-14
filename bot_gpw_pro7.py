# -*- coding: utf-8 -*-

import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import telebot
import yfinance as yf

TOKEN = "8514506509:AAFDIZKCDuDN9sWwW-hMgX3xTP9_HyQGfG0"

FREE_CHANNEL = -1003547751553
PRO_CHANNEL = -1003547751553

PRICE_PLN = 99

# godziny raportów
MORNING_BRIEF_HOUR = 8
MORNING_BRIEF_MINUTE = 45

MARKET_CLOSE_HOUR = 17
MARKET_CLOSE_MINUTE = 10

# interwały automatycznych postów
FREE_PULSE_INTERVAL_MIN = 30
PRO_GAINERS_INTERVAL_MIN = 30
ALERT_INTERVAL_MIN = 60
VOLUME_INTERVAL_MIN = 60

ALERT_MOVE_PCT = 3.0
ALERT_DROP_PCT = -3.0
ALERT_VOLUME_SPIKE = 2.0

WATCHLIST: Dict[str, str] = {
"KGH.WA":"KGHM",
"PKN.WA":"Orlen",
"PKO.WA":"PKO BP",
"CDR.WA":"CD Projekt",
"PZU.WA":"PZU",
"PEO.WA":"Pekao",
"ALE.WA":"Allegro",
"PGE.WA":"PGE",
"DNP.WA":"Dino",
"XTB.WA":"XTB",
"LPP.WA":"LPP",
"JSW.WA":"JSW",
}

bot = telebot.TeleBot(TOKEN)

# --------------------------
# DATA FUNCTIONS
# --------------------------

def safe_history(symbol: str, period: str = "3d"):
    try:
        df = yf.Ticker(symbol).history(period=period)
        if df is None or df.empty:
            return None
        return df
    except:
        return None


def get_last_price(symbol: str) -> Optional[float]:
    df = safe_history(symbol)
    try:
        return float(df["Close"].iloc[-1])
    except:
        return None


def get_daily_change(symbol: str) -> Optional[float]:
    df = safe_history(symbol)
    try:
        prev = float(df["Close"].iloc[-2])
        last = float(df["Close"].iloc[-1])
        return round((last/prev-1)*100,2)
    except:
        return None


def get_volume_ratio(symbol: str) -> Optional[float]:
    df = safe_history(symbol,"7d")
    try:
        prev = float(df["Volume"].iloc[-2])
        last = float(df["Volume"].iloc[-1])
        return round(last/prev,2)
    except:
        return None


def gpw_rows():

    rows=[]

    for s,n in WATCHLIST.items():

        p=get_last_price(s)
        c=get_daily_change(s)

        if p and c!=None:

            rows.append((s,n,c,p))

    return rows


def top_gainers():

    rows=gpw_rows()
    rows.sort(key=lambda x:x[2],reverse=True)

    return rows[:8]


def top_losers():

    rows=gpw_rows()
    rows.sort(key=lambda x:x[2])

    return rows[:8]


def volume_spikes():

    rows=[]

    for s,n in WATCHLIST.items():

        r=get_volume_ratio(s)
        c=get_daily_change(s)
        p=get_last_price(s)

        if r and r>=ALERT_VOLUME_SPIKE:

            rows.append((s,n,r,c,p))

    rows.sort(key=lambda x:x[2],reverse=True)

    return rows[:6]


def alerts():

    out=[]

    for s,n,c,p in gpw_rows():

        r=get_volume_ratio(s) or 1.0

        if c>=ALERT_MOVE_PCT or c<=ALERT_DROP_PCT:

            out.append(f"{n} {c:+.2f}% Vol x{r}")

    return out[:6]


# --------------------------
# MESSAGE BUILDERS
# --------------------------

def free_pulse():

    rows=top_gainers()[:3]

    text="MARKET PULSE\n\n"

    for s,n,c,p in rows:

        text+=f"{n} {c:+.2f}%\n"

    text+="\nKup PRO -> /vip"

    return text


def pro_gainers():

    rows=top_gainers()

    text="TOP GAINERS\n\n"

    for s,n,c,p in rows:

        text+=f"{n} {c:+.2f}% {p:.2f} PLN\n"

    return text


def pro_losers():

    rows=top_losers()

    text="TOP LOSERS\n\n"

    for s,n,c,p in rows:

        text+=f"{n} {c:+.2f}% {p:.2f} PLN\n"

    return text


def volume_alert():

    rows=volume_spikes()

    if not rows:
        return None

    text="VOLUME SPIKE\n\n"

    for s,n,r,c,p in rows:

        text+=f"{n} Vol x{r} {c:+.2f}%\n"

    return text


def move_alert():

    rows=alerts()

    if not rows:
        return None

    text="MOVE ALERT\n\n"

    for r in rows:

        text+=r+"\n"

    return text


def morning_brief():

    text="MORNING BRIEF\n\n"

    for s,n,c,p in top_gainers()[:5]:

        text+=f"{n} {c:+.2f}%\n"

    return text


def market_close():

    text="MARKET CLOSE\n\n"

    for s,n,c,p in top_gainers()[:3]:

        text+=f"Top: {n} {c:+.2f}%\n"

    for s,n,c,p in top_losers()[:3]:

        text+=f"Weak: {n} {c:+.2f}%\n"

    return text


# --------------------------
# TELEGRAM COMMANDS
# --------------------------

@bot.message_handler(commands=['start'])
def start(m):

    bot.reply_to(m,
    "GPW Radar FINAL 1.0\n\n"
    "/pulse\n"
    "/gainers\n"
    "/losers\n"
    "/volume\n"
    "/alerts\n"
    "/brief\n"
    "/vip")


@bot.message_handler(commands=['pulse'])
def pulse(m):

    bot.reply_to(m,free_pulse())


@bot.message_handler(commands=['gainers'])
def gainers(m):

    bot.reply_to(m,pro_gainers())


@bot.message_handler(commands=['losers'])
def losers(m):

    bot.reply_to(m,pro_losers())


@bot.message_handler(commands=['volume'])
def volume(m):

    txt=volume_alert()

    bot.reply_to(m,txt or "Brak volume spike.")


@bot.message_handler(commands=['alerts'])
def alert(m):

    txt=move_alert()

    bot.reply_to(m,txt or "Brak alertów.")


@bot.message_handler(commands=['brief'])
def brief(m):

    bot.reply_to(m,morning_brief())


@bot.message_handler(commands=['vip'])
def vip(m):

    bot.reply_to(m,
    f"GPW Radar PRO\n\nCena: {PRICE_PLN} PLN / miesiac\n\n"
    "Kontakt prywatny po dostęp.")


# --------------------------
# AUTO SCHEDULER
# --------------------------

def run_every(minutes,fn):

    while True:

        try:
            fn()
        except Exception as e:
            print("ERROR",e)

        time.sleep(minutes*60)


def run_daily(hour,minute,fn):

    last=None

    while True:

        now=datetime.now()

        stamp=now.strftime("%Y-%m-%d %H:%M")

        if now.hour==hour and now.minute==minute and stamp!=last:

            try:
                fn()
                last=stamp
            except Exception as e:
                print("ERROR",e)

        time.sleep(20)


# --------------------------
# AUTO POSTS
# --------------------------

def auto_free():

    bot.send_message(FREE_CHANNEL,free_pulse())


def auto_gainers():

    bot.send_message(PRO_CHANNEL,pro_gainers())


def auto_alerts():

    txt=move_alert()

    if txt:

        bot.send_message(PRO_CHANNEL,txt)


def auto_volume():

    txt=volume_alert()

    if txt:

        bot.send_message(PRO_CHANNEL,txt)


def auto_morning():

    bot.send_message(PRO_CHANNEL,morning_brief())


def auto_close():

    bot.send_message(PRO_CHANNEL,market_close())


threading.Thread(target=run_every,args=(FREE_PULSE_INTERVAL_MIN,auto_free),daemon=True).start()
threading.Thread(target=run_every,args=(PRO_GAINERS_INTERVAL_MIN,auto_gainers),daemon=True).start()
threading.Thread(target=run_every,args=(ALERT_INTERVAL_MIN,auto_alerts),daemon=True).start()
threading.Thread(target=run_every,args=(VOLUME_INTERVAL_MIN,auto_volume),daemon=True).start()

threading.Thread(target=run_daily,args=(MORNING_BRIEF_HOUR,MORNING_BRIEF_MINUTE,auto_morning),daemon=True).start()
threading.Thread(target=run_daily,args=(MARKET_CLOSE_HOUR,MARKET_CLOSE_MINUTE,auto_close),daemon=True).start()

# --------------------------
# BOT LOOP
# --------------------------

while True:

    try:

        print("GPW Radar FINAL 1.0 running")

        bot.infinity_polling(timeout=60,long_polling_timeout=60)

    except Exception as e:

        print("BOT ERROR",e)

        time.sleep(10)
