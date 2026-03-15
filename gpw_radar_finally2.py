print("RADAR STARTED")
# -*- coding: utf-8 -*-
import os
import time
import threading
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import telebot
import yfinance as yf

TOKEN = os.getenv("TELEGRAM_TOKEN")
FREE_CHANNEL = os.getenv("FREE_CHANNEL", "@gpwradar")
PRO_CHANNEL = os.getenv("PRO_CHANNEL", "@gpwradarpro")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6522340820"))
PRICE_PLN = int(os.getenv("PRICE_PLN", "99"))
PAYMENT_INFO = os.getenv("PAYMENT_INFO", "BLIK / przelew / kontakt prywatny")

if not TOKEN:
    raise RuntimeError("Brak TELEGRAM_TOKEN w Railway Variables")

bot = telebot.TeleBot(TOKEN, parse_mode=None)
print("BOT OBJECT OK")

GPW: Dict[str, str] = {
    "KGHM": "KGH.WA",
    "Orlen": "PKN.WA",
    "PKO BP": "PKO.WA",
    "CD Projekt": "CDR.WA",
    "PZU": "PZU.WA",
    "Pekao": "PEO.WA",
    "Allegro": "ALE.WA",
    "PGE": "PGE.WA",
    "Dino": "DNP.WA",
    "XTB": "XTB.WA",
    "LPP": "LPP.WA",
    "JSW": "JSW.WA",
}

MACRO: Dict[str, str] = {
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Cocoa": "CC=F",
    "Oil": "CL=F",
    "Gas": "NG=F",
    "Copper": "HG=F",
    "S&P500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DAX": "^GDAXI",
    "WIG20": "^WIG20",
}

LAST_RUN = {"free_pulse": 0.0, "pro_report": 0.0, "pro_alerts": 0.0, "free_promo": 0.0}

def notify_admin(text: str) -> None:
    try:
        bot.send_message(ADMIN_ID, text[:4000])
    except Exception:
        pass

def safe_send(chat_id: str, text: str) -> None:
    try:
        bot.send_message(chat_id, text)
    except Exception as e:
        notify_admin(f"Send error to {chat_id}: {e}")

def market_open() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    return 9 <= now.hour <= 17

def should_run(key: str, interval_seconds: int) -> bool:
    now_ts = time.time()
    if now_ts - LAST_RUN[key] >= interval_seconds:
        LAST_RUN[key] = now_ts
        return True
    return False

def get_df(symbol: str, period: str = "5d"):
    try:
        df = yf.Ticker(symbol).history(period=period, auto_adjust=False)
        if df is None or df.empty:
            return None
        return df
    except Exception:
        return None

def get_change(symbol: str) -> Optional[Tuple[float, float]]:
    df = get_df(symbol, "2d")
    if df is None or len(df) < 2:
        return None
    prev_close = float(df["Close"].iloc[-2])
    last_close = float(df["Close"].iloc[-1])
    if prev_close == 0:
        return None
    change = ((last_close - prev_close) / prev_close) * 100
    return round(last_close, 2), round(change, 2)

def get_signal(symbol: str) -> Optional[str]:
    df = get_df(symbol, "5d")
    if df is None or len(df) < 5:
        return None
    ma_fast = df["Close"].tail(3).mean()
    ma_slow = df["Close"].mean()
    if ma_fast > ma_slow:
        return "BUY"
    elif ma_fast < ma_slow:
        return "SELL"
    return "NEUTRAL"

def build_pulse() -> str:
    rows: List[Tuple[str, float, float]] = []
    for name, symbol in GPW.items():
        result = get_change(symbol)
        if result:
            price, change = result
            rows.append((name, price, change))
    if not rows:
        return "ð MARKET PULSE\n\nBrak danych teraz."
    rows = sorted(rows, key=lambda x: x[2], reverse=True)[:5]
    lines = [f"ð MARKET PULSE ({datetime.now().strftime('%H:%M')})", ""]
    for name, price, change in rows:
        lines.append(f"{name}: {price} PLN ({change:+.2f}%)")
    lines.append("")
    lines.append("PRO â /vip")
    return "\n".join(lines)

def build_macro() -> str:
    lines = [f"ð MACRO RADAR ({datetime.now().strftime('%H:%M')})", ""]
    found = False
    for name, symbol in MACRO.items():
        result = get_change(symbol)
        if result:
            price, change = result
            lines.append(f"{name}: {price} ({change:+.2f}%)")
            found = True
    if not found:
        return "ð MACRO RADAR\n\nBrak danych."
    return "\n".join(lines)

def build_top() -> str:
    rows: List[Tuple[str, float, float]] = []
    for name, symbol in GPW.items():
        result = get_change(symbol)
        if result:
            price, change = result
            rows.append((name, price, change))
    if not rows:
        return "ð TOP MOVERS\n\nBrak danych."
    rows = sorted(rows, key=lambda x: x[2], reverse=True)[:5]
    lines = [f"ð TOP MOVERS ({datetime.now().strftime('%H:%M')})", ""]
    for name, price, change in rows:
        lines.append(f"{name}: {price} PLN ({change:+.2f}%)")
    return "\n".join(lines)

def build_alerts() -> str:
    lines = [f"ð¨ ALERTY ({datetime.now().strftime('%H:%M')})", ""]
    found = False
    for name, symbol in GPW.items():
        result = get_change(symbol)
        if result:
            price, change = result
            signal = get_signal(symbol)
            if abs(change) >= 2.0:
                lines.append(f"{name}: {price} PLN ({change:+.2f}%) | {signal}")
                found = True
    if not found:
        return "ð¨ ALERTY\n\nBrak alertÃ³w teraz."
    return "\n".join(lines)

def build_stats() -> str:
    up = down = flat = 0
    for _, symbol in GPW.items():
        result = get_change(symbol)
        if result:
            _, change = result
            if change > 0:
                up += 1
            elif change < 0:
                down += 1
            else:
                flat += 1
    return f"ð STATS\n\nNa plusie: {up}\nNa minusie: {down}\nBez zmian: {flat}"

def build_locked() -> str:
    return "ð PREMIUM SIGNAL\n\nTicker: ð\nBias: ð\nEntry: ð\nTarget: ð\n\nPeÅna wersja â /vip"

def build_vip() -> str:
    return (
        "ð GPW RADAR PRO\n\n"
        f"Cena: {PRICE_PLN} PLN / miesiÄc\n"
        f"PÅatnoÅÄ: {PAYMENT_INFO}\n\n"
        "Dostajesz:\n- market pulse\n- top movers\n- macro radar\n- alerts\n- locked signals\n- czÄstsze raporty"
    )

@bot.message_handler(commands=["start"])
def start_cmd(message):
    bot.reply_to(message, "GPW RADAR FINAL 2.0\n\n/pulse\n/macro\n/top\n/alerts\n/stats\n/locked\n/vip\n/test")

@bot.message_handler(commands=["pulse"])
def pulse_cmd(message):
    bot.reply_to(message, build_pulse())

@bot.message_handler(commands=["macro"])
def macro_cmd(message):
    bot.reply_to(message, build_macro())

@bot.message_handler(commands=["top"])
def top_cmd(message):
    bot.reply_to(message, build_top())

@bot.message_handler(commands=["alerts"])
def alerts_cmd(message):
    bot.reply_to(message, build_alerts())

@bot.message_handler(commands=["stats"])
def stats_cmd(message):
    bot.reply_to(message, build_stats())

@bot.message_handler(commands=["locked"])
def locked_cmd(message):
    bot.reply_to(message, build_locked())

@bot.message_handler(commands=["vip"])
def vip_cmd(message):
    bot.reply_to(message, build_vip())

@bot.message_handler(commands=["test"])
def test_cmd(message):
    bot.reply_to(message, "GPW Radar dziaÅa â")

def scheduler_loop():
    notify_admin("GPW FINAL 2.0 scheduler start â")
    while True:
        try:
            if market_open():
                if should_run("free_pulse", 60 * 30):
                    safe_send(FREE_CHANNEL, build_pulse())
                if should_run("pro_report", 60 * 60):
                    safe_send(PRO_CHANNEL, build_top())
                    safe_send(PRO_CHANNEL, build_macro())
                if should_run("pro_alerts", 60 * 15):
                    text = build_alerts()
                    if "Brak alertÃ³w" not in text:
                        safe_send(PRO_CHANNEL, text)
                if should_run("free_promo", 60 * 60 * 3):
                    safe_send(FREE_CHANNEL, build_locked())
                    safe_send(FREE_CHANNEL, "ð WiÄcej sygnaÅÃ³w â /vip")
            time.sleep(30)
        except Exception as e:
            notify_admin(f"Scheduler error: {e}")
            time.sleep(60)

def run():
    # usunięcie webhooka aby uniknąć konfliktu
    try:
        bot.remove_webhook()
        time.sleep(2)
    except Exception:
        pass

    threading.Thread(target=scheduler_loop, daemon=True).start()
 
        try:
            print("BEFORE POLLING")
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                skip_pending=True
            )
        except Exception as e:
            print(f"POLLING ERROR: {e}")
            notify_admin(f"Polling error: {e}")
            time.sleep(10)
if __name__ == "__main__":
    run()
