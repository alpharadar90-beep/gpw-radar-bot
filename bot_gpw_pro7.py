# -*- coding: utf-8 -*-

import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import telebot
import yfinance as yf

TOKEN = "8514506509:AAFDIZKCDuDN9sWwW-hMgX3xTP9_HyQGfG0"

FREE_CHANNEL = "@gpwradar"
PRO_CHANNEL = -1003547751553

PRICE_PLN = 99

MORNING_BRIEF_HOUR = 8
MORNING_BRIEF_MINUTE = 45
MARKET_CLOSE_HOUR = 17
MARKET_CLOSE_MINUTE = 10

FREE_PULSE_INTERVAL_MIN = 30
PRO_PULSE_INTERVAL_MIN = 30
BREAKOUT_INTERVAL_MIN = 60
VOLUME_INTERVAL_MIN = 60
ALERT_INTERVAL_MIN = 45

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


def safe_history(symbol: str, period: str = "7d", interval: str = "1d"):
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
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


def get_momentum_3d(symbol: str) -> Optional[float]:
    df = safe_history(symbol, period="10d")
    if df is None or len(df) < 4:
        return None
    try:
        prev = float(df["Close"].iloc[-4])
        last = float(df["Close"].iloc[-1])
        return None if prev == 0 else round((last / prev - 1) * 100, 2)
    except Exception:
        return None


def is_new_high(symbol: str, lookback: int = 20) -> Optional[bool]:
    df = safe_history(symbol, period=f"{lookback + 7}d")
    if df is None or len(df) < lookback + 1:
        return None
    try:
        closes = df["Close"].tail(lookback + 1)
        return float(closes.iloc[-1]) > float(closes.iloc[:-1].max())
    except Exception:
        return None


def is_new_low(symbol: str, lookback: int = 20) -> Optional[bool]:
    df = safe_history(symbol, period=f"{lookback + 7}d")
    if df is None or len(df) < lookback + 1:
        return None
    try:
        closes = df["Close"].tail(lookback + 1)
        return float(closes.iloc[-1]) < float(closes.iloc[:-1].min())
    except Exception:
        return None


def fmt_price(symbol: str, price: float) -> str:
    if symbol.endswith(".WA"):
        return f"{price:.2f} PLN"
    if symbol.endswith("=X"):
        return f"{price:.4f}"
    if symbol.startswith("^"):
        return f"{price:.2f}"
    return f"${price:.2f}"


def safe_send(target: str, text: str, label: str) -> None:
    try:
        channel = FREE_CHANNEL if target == "free" else PRO_CHANNEL
        bot.send_message(channel, text)
        print(f"{label} sent")
    except Exception as e:
        print(f"{label} error: {e}")


def compose_free_message(title: str, lines: List[str]) -> str:
    body = "\n".join([x for x in lines if x]).strip()
    return f"{title} ({now_label()})\n\n{body}\n\nKup PRO -> /vip"


def compose_pro_message(title: str, lines: List[str]) -> str:
    body = "\n".join([x for x in lines if x]).strip()
    return (
        f"{title} ({now_label()})\n\n{body}\n\n"
        f"GPW Radar PRO\nCena: {PRICE_PLN} PLN / miesiac\n/payment"
    )


def gpw_rows() -> List[Tuple[str, str, float, float]]:
    rows = []
    for symbol, name in WATCHLIST.items():
        price = get_last_price(symbol)
        change = get_daily_change_pct(symbol)
        if price is not None and change is not None:
            rows.append((symbol, name, change, price))
    return rows


def top_gainers(limit: int = 10):
    rows = gpw_rows()
    rows.sort(key=lambda x: x[2], reverse=True)
    return rows[:limit]


def top_losers(limit: int = 10):
    rows = gpw_rows()
    rows.sort(key=lambda x: x[2])
    return rows[:limit]


def volume_spikes(limit: int = 8):
    rows = []
    for symbol, name in WATCHLIST.items():
        ratio = get_volume_spike_ratio(symbol)
        price = get_last_price(symbol)
        change = get_daily_change_pct(symbol)
        if ratio is not None and price is not None and change is not None and ratio >= ALERT_VOLUME_SPIKE:
            rows.append((symbol, name, ratio, change, price))
    rows.sort(key=lambda x: x[2], reverse=True)
    return rows[:limit]


def breakouts(limit: int = 8):
    out = []
    for symbol, name in WATCHLIST.items():
        price = get_last_price(symbol)
        change = get_daily_change_pct(symbol)
        if price is None or change is None:
            continue
        high = is_new_high(symbol, 20)
        low = is_new_low(symbol, 20)
        if high:
            out.append(f"{name} | NEW 20D HIGH | {fmt_price(symbol, price)} | {change:+.2f}%")
        elif low:
            out.append(f"{name} | NEW 20D LOW | {fmt_price(symbol, price)} | {change:+.2f}%")
    return out[:limit]


def move_alerts(limit: int = 8):
    out = []
    for symbol, name, change, price in gpw_rows():
        ratio = get_volume_spike_ratio(symbol) or 1.0
        if change >= ALERT_MOVE_PCT or change <= ALERT_DROP_PCT:
            out.append(f"{name} | {fmt_price(symbol, price)} | {change:+.2f}% | Vol x{ratio:.2f}")
    return out[:limit]


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

    label = "Strong" if score >= 8 else "Constructive" if score >= 6 else "Mixed" if score >= 4 else "Weak"
    return score, label


def macro_rows(limit: int = 5):
    rows = []
    for symbol, name in MACRO_SYMBOLS.items():
        price = get_last_price(symbol)
        change = get_daily_change_pct(symbol)
        if price is not None and change is not None:
            rows.append((symbol, name, change, price))
    rows.sort(key=lambda x: abs(x[2]), reverse=True)
    return rows[:limit]


def build_free_pulse() -> str:
    score, label = market_score()
    lines = (
        ["GPW"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in top_gainers(3)]
        + ["", "Macro"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in macro_rows(3)]
        + ["", f"Strength: {score}/10 ({label})"]
    )
    return compose_free_message("MARKET PULSE", lines)


def build_pro_gainers() -> str:
    lines = [f"{name} | {change:+.2f}% | {fmt_price(symbol, price)}" for symbol, name, change, price in top_gainers(8)]
    return compose_pro_message("TOP GAINERS", lines or ["Brak danych"])


def build_pro_losers() -> str:
    lines = [f"{name} | {change:+.2f}% | {fmt_price(symbol, price)}" for symbol, name, change, price in top_losers(8)]
    return compose_pro_message("TOP LOSERS", lines or ["Brak danych"])


def build_volume_spike() -> Optional[str]:
    rows = volume_spikes(8)
    if not rows:
        return None
    lines = [f"{name} | Vol x{ratio:.2f} | {change:+.2f}% | {fmt_price(symbol, price)}" for symbol, name, ratio, change, price in rows]
    return compose_pro_message("VOLUME SPIKE", lines)


def build_breakouts() -> Optional[str]:
    rows = breakouts(8)
    if not rows:
        return None
    return compose_pro_message("BREAKOUTS", rows)


def build_alerts() -> Optional[str]:
    rows = move_alerts(8)
    if not rows:
        return None
    return compose_pro_message("MOVE ALERTS", rows)


def build_morning_brief() -> str:
    score, label = market_score()
    lines = (
        ["Top Gainers"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in top_gainers(5)]
        + ["", "Top Losers"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in top_losers(5)]
        + ["", "Macro Focus"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in macro_rows(5)]
        + ["", f"Market Strength: {score}/10 ({label})"]
    )
    return compose_pro_message("MORNING BRIEF", lines)


def build_market_close() -> str:
    score, label = market_score()
    lines = (
        ["Best of day"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in top_gainers(5)]
        + ["", "Worst of day"]
        + [f"{name} {change:+.2f}%" for _, name, change, _ in top_losers(5)]
        + ["", f"Closing Strength: {score}/10 ({label})"]
    )
    return compose_pro_message("MARKET CLOSE", lines)


@bot.message_handler(commands=["start"])
def cmd_start(message):
    bot.reply_to(
        message,
        "GPW Radar PRO11\n\n"
        "/pulse\n/gainers\n/losers\n/breakouts\n/volume\n/alerts\n/vip\n/payment"
    )


@bot.message_handler(commands=["pulse"])
def cmd_pulse(message):
    bot.reply_to(message, build_free_pulse())


@bot.message_handler(commands=["gainers"])
def cmd_gainers(message):
    bot.reply_to(message, build_pro_gainers())


@bot.message_handler(commands=["losers"])
def cmd_losers(message):
    bot.reply_to(message, build_pro_losers())


@bot.message_handler(commands=["breakouts"])
def cmd_breakouts(message):
    bot.reply_to(message, build_breakouts() or "Brak breakoutow teraz.")


@bot.message_handler(commands=["volume"])
def cmd_volume(message):
    bot.reply_to(message, build_volume_spike() or "Brak volume spike teraz.")


@bot.message_handler(commands=["alerts"])
def cmd_alerts(message):
    bot.reply_to(message, build_alerts() or "Brak alertow ruchu teraz.")


@bot.message_handler(commands=["vip"])
def cmd_vip(message):
    bot.reply_to(
        message,
        f"GPW Radar PRO\n\nCena: {PRICE_PLN} PLN / miesiac\n\n"
        "Co dostajesz:\n"
        "- Top Gainers / Losers\n"
        "- Breakouts\n"
        "- Volume Spike\n"
        "- Move Alerts\n"
        "- Morning Brief\n"
        "- Market Close\n\n"
        "/payment"
    )


@bot.message_handler(commands=["payment"])
def cmd_payment(message):
    bot.reply_to(message, "Platnosc: BLIK / przelew / kontakt prywatny")


def run_every(minutes: int, fn, label: str):
    while True:
        try:
            fn()
        except Exception as e:
            print(f"{label} error: {e}")
        time.sleep(minutes * 60)


def run_daily(hour: int, minute: int, fn, label: str):
    last_stamp = None
    while True:
        try:
            now = datetime.now()
            stamp = now.strftime("%Y-%m-%d %H:%M")
            if now.hour == hour and now.minute == minute and stamp != last_stamp:
                fn()
                last_stamp = stamp
        except Exception as e:
            print(f"{label} error: {e}")
        time.sleep(20)


def auto_free_pulse():
    safe_send("free", build_free_pulse(), "free_pulse")


def auto_pro_gainers():
    safe_send("pro", build_pro_gainers(), "pro_gainers")


def auto_breakouts():
    txt = build_breakouts()
    if txt:
        safe_send("pro", txt, "breakouts")


def auto_volume():
    txt = build_volume_spike()
    if txt:
        safe_send("pro", txt, "volume")


def auto_alerts():
    txt = build_alerts()
    if txt:
        safe_send("pro", txt, "alerts")


def auto_morning():
    safe_send("pro", build_morning_brief(), "morning")


def auto_close():
    safe_send("pro", build_market_close(), "close")


threading.Thread(target=run_every, args=(FREE_PULSE_INTERVAL_MIN, auto_free_pulse, "free_pulse_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(PRO_PULSE_INTERVAL_MIN, auto_pro_gainers, "pro_gainers_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(BREAKOUT_INTERVAL_MIN, auto_breakouts, "breakouts_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(VOLUME_INTERVAL_MIN, auto_volume, "volume_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(ALERT_INTERVAL_MIN, auto_alerts, "alerts_thread"), daemon=True).start()
threading.Thread(target=run_daily, args=(MORNING_BRIEF_HOUR, MORNING_BRIEF_MINUTE, auto_morning, "morning_thread"), daemon=True).start()
threading.Thread(target=run_daily, args=(MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE, auto_close, "close_thread"), daemon=True).start()


while True:
    try:
        print("GPW Radar PRO11 bot started...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("BOT ERROR:", e)
        print("Restart in 10 seconds...")
        time.sleep(10)
