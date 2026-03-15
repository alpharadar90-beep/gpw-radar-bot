# -*- coding: utf-8 -*-

import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import telebot
import yfinance as yf
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")

FREE_CHANNEL = -1003547751553
PRO_CHANNEL = -1003547751553

PRICE_PLN = 99
PAYMENT_INFO = "BLIK / przelew / kontakt prywatny"

MORNING_BRIEF_HOUR = 8
MORNING_BRIEF_MINUTE = 45
MARKET_CLOSE_HOUR = 17
MARKET_CLOSE_MINUTE = 10

FREE_PULSE_INTERVAL_MIN = 30
FREE_MARKETING_INTERVAL_MIN = 180
PRO_GAINERS_INTERVAL_MIN = 60
PRO_LOSERS_INTERVAL_MIN = 90
PRO_VOLUME_INTERVAL_MIN = 90
PRO_ALERTS_INTERVAL_MIN = 60
PRO_AI_INTERVAL_MIN = 240

ALERT_MOVE_PCT = 3.0
ALERT_DROP_PCT = -3.0
ALERT_VOLUME_SPIKE = 2.0

WATCHLIST: Dict[str, str] = {
    "KGH.WA": "KGHM",
    "PKN.WA": "Orlen",
    "PKO.WA": "PKO BP",
    "CDR.WA": "CD Projekt",
    "PZU.WA": "PZU",
    "PEO.WA": "Pekao",
    "ALE.WA": "Allegro",
    "PGE.WA": "PGE",
    "DNP.WA": "Dino",
    "XTB.WA": "XTB",
    "LPP.WA": "LPP",
    "JSW.WA": "JSW",
    "BDX.WA": "Budimex",
    "MBK.WA": "mBank",
    "SPL.WA": "Santander PL",
    "ING.WA": "ING BSK",
    "ATT.WA": "Grupa Azoty",
}

MACRO_SYMBOLS: Dict[str, str] = {
    "GC=F": "Gold",
    "SI=F": "Silver",
    "CL=F": "Oil",
    "NG=F": "Natural Gas",
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
    "^GDAXI": "DAX",
    "EURUSD=X": "EUR/USD",
    "EURPLN=X": "EUR/PLN",
    "USDPLN=X": "USD/PLN",
    "BTC-USD": "Bitcoin",
}

bot = telebot.TeleBot(TOKEN, parse_mode=None)

def now_label() -> str:
    return datetime.now().strftime("%H:%M")

def safe_history(symbol: str, period: str = "7d"):
    try:
        df = yf.Ticker(symbol).history(period=period, auto_adjust=False)
        if df is None or df.empty:
            return None
        return df
    except Exception:
        return None

def get_last_price(symbol: str) -> Optional[float]:
    df = safe_history(symbol, period="3d")
    try:
        return None if df is None else float(df["Close"].iloc[-1])
    except Exception:
        return None

def get_daily_change_pct(symbol: str) -> Optional[float]:
    df = safe_history(symbol, period="3d")
    if df is None or len(df) < 2:
        return None
    try:
        prev_close = float(df["Close"].iloc[-2])
        last_close = float(df["Close"].iloc[-1])
        return None if prev_close == 0 else round((last_close / prev_close - 1) * 100, 2)
    except Exception:
        return None

def get_volume_spike_ratio(symbol: str) -> Optional[float]:
    df = safe_history(symbol, period="7d")
    if df is None or len(df) < 3:
        return None
    try:
        prev_vol = float(df["Volume"].iloc[-2])
        last_vol = float(df["Volume"].iloc[-1])
        return None if prev_vol <= 0 else round(last_vol / prev_vol, 2)
    except Exception:
        return None

def safe_send(channel, text: str, label: str) -> None:
    try:
        bot.send_message(channel, text)
        print(f"{label} sent")
    except Exception as e:
        print(f"{label} error: {e}")

def market_is_open() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    current_minutes = now.hour * 60 + now.minute
    return 9 * 60 <= current_minutes <= 17 * 60 + 10

def gpw_rows() -> List[Tuple[str, str, float, float]]:
    rows = []
    for symbol, name in WATCHLIST.items():
        price = get_last_price(symbol)
        change = get_daily_change_pct(symbol)
        if price is not None and change is not None:
            rows.append((symbol, name, change, price))
    return rows

def top_gainers(limit: int = 8):
    rows = gpw_rows()
    rows.sort(key=lambda x: x[2], reverse=True)
    return rows[:limit]

def top_losers(limit: int = 8):
    rows = gpw_rows()
    rows.sort(key=lambda x: x[2])
    return rows[:limit]

def volume_spikes(limit: int = 6):
    rows = []
    for symbol, name in WATCHLIST.items():
        ratio = get_volume_spike_ratio(symbol)
        change = get_daily_change_pct(symbol)
        price = get_last_price(symbol)
        if ratio is not None and change is not None and price is not None and ratio >= ALERT_VOLUME_SPIKE:
            rows.append((symbol, name, ratio, change, price))
    rows.sort(key=lambda x: x[2], reverse=True)
    return rows[:limit]

def move_alerts(limit: int = 6):
    rows = []
    for symbol, name, change, price in gpw_rows():
        ratio = get_volume_spike_ratio(symbol) or 1.0
        if change >= ALERT_MOVE_PCT or change <= ALERT_DROP_PCT:
            rows.append((symbol, name, change, ratio, price))
    rows.sort(key=lambda x: abs(x[2]), reverse=True)
    return rows[:limit]

def macro_rows(limit: int = 4):
    rows = []
    for symbol, name in MACRO_SYMBOLS.items():
        price = get_last_price(symbol)
        change = get_daily_change_pct(symbol)
        if price is not None and change is not None:
            rows.append((symbol, name, change, price))
    rows.sort(key=lambda x: abs(x[2]), reverse=True)
    return rows[:limit]

def market_score() -> Tuple[int, str]:
    rows = gpw_rows()
    if not rows:
        return 0, "Brak danych"
    positives = sum(1 for _, _, c, _ in rows if c > 0)
    negatives = sum(1 for _, _, c, _ in rows if c < 0)
    avg = sum(c for _, _, c, _ in rows) / len(rows)
    score = 5
    score += 1 if positives > negatives else -1
    score += 1 if avg > 0.5 else (-1 if avg < -0.5 else 0)
    score = max(0, min(10, score))
    if score >= 8:
        label = "Strong"
    elif score >= 6:
        label = "Constructive"
    elif score >= 4:
        label = "Mixed"
    else:
        label = "Weak"
    return score, label

def compose_free(title: str, lines: List[str]) -> str:
    body = "\n".join([x for x in lines if x]).strip()
    return f"{title} ({now_label()})\n\n{body}\n\nKup PRO -> /vip"

def compose_pro(title: str, lines: List[str]) -> str:
    body = "\n".join([x for x in lines if x]).strip()
    return f"{title} ({now_label()})\n\n{body}\n\nGPW Radar PRO\nCena: {PRICE_PLN} PLN / miesiac\n/payment"

def build_free_pulse() -> str:
    score, label = market_score()
    lines = (
        ["GPW"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in top_gainers(3)]
        + ["", "Macro"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in macro_rows(3)]
        + ["", f"Strength: {score}/10 ({label})"]
    )
    return compose_free("MARKET PULSE", lines)

def build_free_marketing() -> str:
    score, label = market_score()
    lines = [f"Market Strength Score: {score}/10 ({label})"] + [f"{name} {change:+.2f}%" for _, name, change, _ in top_gainers(2)] + ["", "Trial PRO -> /trial", "Full signals -> @gpwradarpro"]
    return compose_free("FREE -> PRO", lines)

def build_gainers() -> str:
    lines = [f"{name} | {change:+.2f}% | {price:.2f} PLN" for _, name, change, price in top_gainers()]
    return compose_pro("TOP GAINERS", lines or ["Brak danych"])

def build_losers() -> str:
    lines = [f"{name} | {change:+.2f}% | {price:.2f} PLN" for _, name, change, price in top_losers()]
    return compose_pro("TOP LOSERS", lines or ["Brak danych"])

def build_volume() -> Optional[str]:
    rows = volume_spikes()
    if not rows:
        return None
    lines = [f"{name} | Vol x{ratio:.2f} | {change:+.2f}% | {price:.2f} PLN" for _, name, ratio, change, price in rows]
    return compose_pro("VOLUME SPIKE", lines)

def build_alerts() -> Optional[str]:
    rows = move_alerts()
    if not rows:
        return None
    lines = [f"{name} | {change:+.2f}% | Vol x{ratio:.2f} | {price:.2f} PLN" for _, name, change, ratio, price in rows]
    return compose_pro("MOVE ALERTS", lines)

def build_brief() -> str:
    score, label = market_score()
    lines = (
        ["Top Gainers"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in top_gainers(5)]
        + ["", "Top Losers"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in top_losers(5)]
        + ["", f"Market Strength: {score}/10 ({label})"]
    )
    return compose_pro("MORNING BRIEF", lines)

def build_close() -> str:
    score, label = market_score()
    lines = (
        ["Best of day"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in top_gainers(3)]
        + ["", "Worst of day"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in top_losers(3)]
        + ["", f"Closing Strength: {score}/10 ({label})"]
    )
    return compose_pro("MARKET CLOSE", lines)

def build_ai() -> str:
    score, label = market_score()
    leaders = top_gainers(3)
    laggards = top_losers(3)
    lines = [f"Market regime: {label} ({score}/10)", "", "Leaders"]
    lines += [f"- {name} {change:+.2f}%" for _, name, change, _ in leaders]
    lines += ["", "Weak names"]
    lines += [f"- {name} {change:+.2f}%" for _, name, change, _ in laggards]
    if score >= 7:
        lines += ["", "AI view: Momentum improving. Focus on strength and breakouts."]
    elif score <= 3:
        lines += ["", "AI view: Defensive tape. Avoid weak names and low volume setups."]
    else:
        lines += ["", "AI view: Mixed market. Prefer selective trades only."]
    return compose_pro("AI MARKET INSIGHT", lines)

def build_tweet() -> str:
    top = top_gainers(1)
    if not top:
        return "Brak danych do posta na X."
    _, name, change, _ = top[0]
    return (
        "ð¨ GPW ALERT\n\n"
        f"{name} {change:+.2f}%\n"
        "Detected by GPW Radar.\n\n"
        "Trial PRO -> /trial\n"
        "Telegram: t.me/gpwradar\n\n"
        "#GPW #Gielda #Trading"
    )

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "GPW Radar FINAL 1.2\n\n/pulse\n/gainers\n/losers\n/volume\n/alerts\n/brief\n/ai\n/tweet\n/trial\n/vip\n/payment")

@bot.message_handler(commands=['pulse'])
def pulse(m):
    bot.reply_to(m, build_free_pulse())

@bot.message_handler(commands=['gainers'])
def gainers(m):
    bot.reply_to(m, build_gainers())

@bot.message_handler(commands=['losers'])
def losers(m):
    bot.reply_to(m, build_losers())

@bot.message_handler(commands=['volume'])
def volume_cmd(m):
    bot.reply_to(m, build_volume() or "Brak volume spike.")

@bot.message_handler(commands=['alerts'])
def alerts_cmd(m):
    bot.reply_to(m, build_alerts() or "Brak alertow.")

@bot.message_handler(commands=['brief'])
def brief_cmd(m):
    bot.reply_to(m, build_brief())

@bot.message_handler(commands=['ai'])
def ai_cmd(m):
    bot.reply_to(m, build_ai())

@bot.message_handler(commands=['tweet'])
def tweet_cmd(m):
    bot.reply_to(m, build_tweet())

@bot.message_handler(commands=['trial'])
def trial_cmd(m):
    bot.reply_to(m, "ð Trial PRO aktywowany na 24h\n\nMasz dostep do:\n- Alerts\n- Volume Spike\n- AI Insight\n- Morning Brief\n- Market Close\n\nJesli chcesz pelny dostep:\n/vip")

@bot.message_handler(commands=['vip'])
def vip_cmd(m):
    bot.reply_to(m, f"GPW Radar PRO\n\nCena: {PRICE_PLN} PLN / miesiac\n\nCo dostajesz:\n- Market Pulse\n- Top Gainers / Losers\n- Volume Spike\n- Move Alerts\n- Morning Brief\n- Market Close\n- AI Market Insight\n\n/payment")

@bot.message_handler(commands=['payment'])
def payment_cmd(m):
    bot.reply_to(m, f"Platnosc: {PAYMENT_INFO}")

LAST_RUN = {}

def should_run(key: str, minutes: int) -> bool:
    now = time.time()
    last = LAST_RUN.get(key, 0)
    if now - last >= minutes * 60:
        LAST_RUN[key] = now
        return True
    return False

def run_scheduler():
    while True:
        try:
            if market_is_open():
                if should_run("free_pulse", FREE_PULSE_INTERVAL_MIN):
                    safe_send(FREE_CHANNEL, build_free_pulse(), "free_pulse")
                if should_run("free_marketing", FREE_MARKETING_INTERVAL_MIN):
                    safe_send(FREE_CHANNEL, build_free_marketing(), "free_marketing")
                if should_run("pro_gainers", PRO_GAINERS_INTERVAL_MIN):
                    safe_send(PRO_CHANNEL, build_gainers(), "pro_gainers")
                if should_run("pro_losers", PRO_LOSERS_INTERVAL_MIN):
                    safe_send(PRO_CHANNEL, build_losers(), "pro_losers")
                if should_run("pro_volume", PRO_VOLUME_INTERVAL_MIN):
                    txt = build_volume()
                    if txt:
                        safe_send(PRO_CHANNEL, txt, "pro_volume")
                if should_run("pro_alerts", PRO_ALERTS_INTERVAL_MIN):
                    txt = build_alerts()
                    if txt:
                        safe_send(PRO_CHANNEL, txt, "pro_alerts")
                if should_run("pro_ai", PRO_AI_INTERVAL_MIN):
                    safe_send(PRO_CHANNEL, build_ai(), "pro_ai")

            now = datetime.now()
            stamp = now.strftime("%Y-%m-%d %H:%M")
            if now.hour == MORNING_BRIEF_HOUR and now.minute == MORNING_BRIEF_MINUTE:
                if LAST_RUN.get("morning_stamp") != stamp:
                    safe_send(PRO_CHANNEL, build_brief(), "morning_brief")
                    LAST_RUN["morning_stamp"] = stamp
            if now.hour == MARKET_CLOSE_HOUR and now.minute == MARKET_CLOSE_MINUTE:
                if LAST_RUN.get("close_stamp") != stamp:
                    safe_send(PRO_CHANNEL, build_close(), "market_close")
                    LAST_RUN["close_stamp"] = stamp
        except Exception as e:
            print("scheduler error:", e)
        time.sleep(60)

if __name__ == "__main__":
    print("GPW Radar FINAL 1.2 running")
    threading.Thread(target=run_scheduler, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print("BOT ERROR", e)
            time.sleep(10)
