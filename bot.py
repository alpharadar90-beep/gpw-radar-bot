# -*- coding: utf-8 -*-
"""
AlphaRadar Final 1.0
DEX + Binance Spot + Binance Futures + AI score + Whale logic
Stable single-scheduler architecture for Railway
"""

import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import telebot
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")

FREE_CHANNEL = "@AlphaRadarSignals"
VIP_CHANNEL = "@AlphaRadarVIP"

PRICE_USD = 29
PAYMENT_INFO = "USDT TRC20 / kontakt prywatny"
USDT_TRC20_ADDRESS = "WSTAW_ADRES_USDT_TRC20"

BINANCE_SPOT_24H = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_FUTURES_24H = "https://fapi.binance.com/fapi/v1/ticker/24hr"
DEX_PROFILES = "https://api.dexscreener.com/token-profiles/latest/v1"
DEX_BOOSTS = "https://api.dexscreener.com/token-boosts/top/v1"

ALLOWED_CHAINS = {"solana", "ethereum", "base"}
MIN_LIQUIDITY_USD = 80000
MIN_VOLUME_USD = 10000
MIN_AI_SCORE = 7.5

FREE_PULSE_INTERVAL_MIN = 30
FREE_HYPE_INTERVAL_MIN = 180
FREE_INVITE_INTERVAL_MIN = 360

VIP_TOP_INTERVAL_MIN = 30
VIP_AI_INTERVAL_MIN = 120
VIP_DEX_INTERVAL_MIN = 10
VIP_FUTURES_INTERVAL_MIN = 15

REQUEST_TIMEOUT = 20

bot = telebot.TeleBot(TOKEN, parse_mode=None)
LAST_RUN: Dict[str, float] = {}
LAST_TEXT: Dict[str, str] = {}


def now_label() -> str:
    return datetime.now().strftime("%H:%M")


def fetch_json(url: str) -> Any:
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("fetch_json error:", url, e)
        return None


def safe_send(channel: str, text: str, label: str) -> None:
    try:
        if LAST_TEXT.get(label) == text:
            print(f"{label} skipped duplicate")
            return
        bot.send_message(channel, text)
        LAST_TEXT[label] = text
        print(f"{label} sent")
    except Exception as e:
        print(f"{label} error:", e)


def should_run(key: str, minutes: int) -> bool:
    now = time.time()
    last = LAST_RUN.get(key, 0)
    if now - last >= minutes * 60:
        LAST_RUN[key] = now
        return True
    return False


def is_stable_pair(symbol: str) -> bool:
    stable_quotes = ("USDT", "USDC", "BUSD", "FDUSD")
    return any(symbol.endswith(q) for q in stable_quotes)


def get_binance_spot_rows(limit: int = 10) -> List[Dict[str, Any]]:
    data = fetch_json(BINANCE_SPOT_24H)
    if not isinstance(data, list):
        return []

    rows: List[Dict[str, Any]] = []
    for item in data:
        try:
            symbol = item["symbol"]
            if not is_stable_pair(symbol):
                continue
            change = float(item["priceChangePercent"])
            last_price = float(item["lastPrice"])
            quote_volume = float(item["quoteVolume"])
            rows.append({
                "symbol": symbol,
                "change": change,
                "price": last_price,
                "quote_volume": quote_volume,
            })
        except Exception:
            continue

    rows.sort(key=lambda x: x["change"], reverse=True)
    return rows[:limit]


def futures_score(change: float, quote_volume: float, count: int) -> float:
    score = 0.0

    if abs(change) >= 3:
        score += 2.5
    elif abs(change) >= 2:
        score += 1.5
    elif abs(change) >= 1:
        score += 0.5

    if quote_volume >= 100000000:
        score += 3.0
    elif quote_volume >= 25000000:
        score += 2.0
    elif quote_volume >= 5000000:
        score += 1.0

    if count >= 100000:
        score += 2.0
    elif count >= 30000:
        score += 1.0

    return round(min(score, 10.0), 2)


def get_futures_rows(limit: int = 8) -> List[Dict[str, Any]]:
    data = fetch_json(BINANCE_FUTURES_24H)
    if not isinstance(data, list):
        return []

    rows: List[Dict[str, Any]] = []
    for item in data:
        try:
            symbol = item["symbol"]
            if not symbol.endswith("USDT"):
                continue
            change = float(item["priceChangePercent"])
            last_price = float(item["lastPrice"])
            quote_volume = float(item["quoteVolume"])
            count = int(item.get("count", 0))
            score = futures_score(change, quote_volume, count)
            if score < 3.0:
                continue
            rows.append({
                "symbol": symbol,
                "change": change,
                "price": last_price,
                "quote_volume": quote_volume,
                "count": count,
                "futures_score": score,
            })
        except Exception:
            continue

    rows.sort(key=lambda x: x["futures_score"], reverse=True)
    return rows[:limit]


def normalize_chain(chain: Optional[str]) -> str:
    if not chain:
        return ""
    return str(chain).strip().lower()


def ai_score(liquidity: float, volume: float, change: float, boost: float, chain: str) -> float:
    score = 0.0

    if liquidity >= 500000:
        score += 2.5
    elif liquidity >= 250000:
        score += 2.0
    elif liquidity >= 120000:
        score += 1.5
    elif liquidity >= MIN_LIQUIDITY_USD:
        score += 1.0

    if volume >= 1000000:
        score += 2.5
    elif volume >= 300000:
        score += 2.0
    elif volume >= 100000:
        score += 1.5
    elif volume >= MIN_VOLUME_USD:
        score += 1.0

    if change >= 50:
        score += 2.0
    elif change >= 20:
        score += 1.5
    elif change >= 8:
        score += 1.0
    elif change >= 3:
        score += 0.5

    if boost >= 1000:
        score += 1.5
    elif boost >= 300:
        score += 1.0
    elif boost > 0:
        score += 0.5

    if chain == "solana":
        score += 1.0
    elif chain in {"ethereum", "base"}:
        score += 0.7

    return round(min(score, 10.0), 2)


def classify_signal(score: float, volume: float, liquidity: float, change: float) -> str:
    ratio = volume / liquidity if liquidity > 0 else 0

    if score >= 9 and ratio >= 1.0:
        return "SMART MONEY"
    if score >= 8 and ratio >= 0.7:
        return "EARLY PUMP"
    if ratio >= 1.5 and liquidity >= 100000:
        return "WHALE ACTIVITY"
    if score >= 7.5:
        return "STRONG MOMENTUM"
    return "WATCH"


def get_dex_candidates(limit: int = 8) -> List[Dict[str, Any]]:
    profiles = fetch_json(DEX_PROFILES)
    boosts = fetch_json(DEX_BOOSTS)

    boost_map: Dict[str, float] = {}
    if isinstance(boosts, list):
        for item in boosts:
            try:
                token_addr = item.get("tokenAddress") or item.get("address") or ""
                amount = float(item.get("amount", 0) or 0)
                if token_addr:
                    boost_map[token_addr] = max(boost_map.get(token_addr, 0.0), amount)
            except Exception:
                continue

    rows: List[Dict[str, Any]] = []
    if not isinstance(profiles, list):
        return rows

    for item in profiles:
        try:
            chain = normalize_chain(item.get("chainId") or item.get("chain"))
            if chain not in ALLOWED_CHAINS:
                continue

            liquidity = float(item.get("liquidity", 0) or 0)
            volume = float(item.get("volume24h", 0) or item.get("volume", 0) or 0)
            change = float(item.get("priceChange24h", 0) or item.get("priceChange", 0) or 0)
            price = float(item.get("priceUsd", 0) or 0)
            token = item.get("tokenSymbol") or item.get("symbol") or "UNKNOWN"
            pair = item.get("pairAddress") or ""
            token_addr = item.get("tokenAddress") or item.get("address") or ""
            boost = boost_map.get(token_addr, 0.0)

            if liquidity < MIN_LIQUIDITY_USD or volume < MIN_VOLUME_USD or price <= 0:
                continue

            score = ai_score(liquidity, volume, change, boost, chain)
            label = classify_signal(score, volume, liquidity, change)
            if score < MIN_AI_SCORE:
                continue

            rows.append({
                "token": token,
                "chain": chain.upper(),
                "price": price,
                "liquidity": liquidity,
                "volume": volume,
                "change": change,
                "boost": boost,
                "score": score,
                "label": label,
                "pair": pair,
            })
        except Exception:
            continue

    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows[:limit]


def build_free_pulse() -> str:
    rows = get_binance_spot_rows(5)
    if not rows:
        return "AlphaRadar Market Pulse\n\nBrak danych teraz."

    lines = [f"{r['symbol']} {r['change']:+.2f}%" for r in rows[:3]]
    return (
        f"ð¨ AlphaRadar Market Pulse ({now_label()})\n\n"
        + "\n".join(lines)
        + "\n\nMore signals -> @AlphaRadarVIPBot"
    )


def build_free_hype() -> str:
    return (
        f"ð AlphaRadar LIVE ({now_label()})\n\n"
        "Scanning:\n"
        "â¢ Binance spot\n"
        "â¢ Futures momentum\n"
        "â¢ DEX early tokens\n"
        "â¢ Smart money\n\n"
        "Trial PRO -> /trial"
    )


def build_free_invite() -> str:
    return (
        f"ð AlphaRadar Community ({now_label()})\n\n"
        "Free channel:\n"
        "â¢ market pulse\n"
        "â¢ top movers\n\n"
        "VIP:\n"
        "â¢ AI pump detection\n"
        "â¢ whale activity\n"
        "â¢ smart money alerts\n\n"
        "Join PRO -> /vip"
    )


def build_top_movers() -> str:
    rows = get_binance_spot_rows(8)
    if not rows:
        return "Top Movers\n\nBrak danych."
    lines = [f"{r['symbol']} | {r['change']:+.2f}% | ${r['price']:.6f}" for r in rows]
    return (
        f"ð TOP MOVERS ({now_label()})\n\n"
        + "\n".join(lines)
        + f"\n\nAlphaRadar VIP\nCena: ${PRICE_USD}/month\n/payment"
    )


def build_futures_alert() -> Optional[str]:
    rows = get_futures_rows(5)
    if not rows:
        return None
    lines = [
        f"{r['symbol']} | {r['change']:+.2f}% | Score {r['futures_score']}/10 | Vol ${r['quote_volume']:.0f}"
        for r in rows
    ]
    return (
        f"ð FUTURES MOMENTUM ({now_label()})\n\n"
        + "\n".join(lines)
        + f"\n\nAlphaRadar VIP\nCena: ${PRICE_USD}/month\n/payment"
    )


def build_ai_ranking() -> Optional[str]:
    rows = get_dex_candidates(5)
    if not rows:
        return None
    lines = [
        f"{i+1}. {r['token']} | {r['label']} | Score {r['score']}/10 | {r['chain']}"
        for i, r in enumerate(rows)
    ]
    return (
        f"ð§  ALPHARADAR AI RANKING ({now_label()})\n\n"
        + "\n".join(lines)
        + f"\n\nAlphaRadar VIP\nCena: ${PRICE_USD}/month\n/payment"
    )


def build_dex_alert() -> Optional[str]:
    rows = get_dex_candidates(1)
    if not rows:
        return None
    r = rows[0]
    return (
        f"ð¨ {r['label']} ({now_label()})\n\n"
        f"Token: {r['token']}\n"
        f"Chain: {r['chain']}\n"
        f"Price: ${r['price']:.8f}\n"
        f"Liquidity: ${r['liquidity']:.0f}\n"
        f"Volume 24h: ${r['volume']:.0f}\n"
        f"Change 24h: {r['change']:+.2f}%\n"
        f"Boost: {r['boost']:.0f}\n"
        f"AI Score: {r['score']}/10\n\n"
        f"AlphaRadar VIP\nCena: ${PRICE_USD}/month\n/payment"
    )


def build_tweet() -> str:
    rows = get_binance_spot_rows(1)
    if not rows:
        return "Brak danych do posta na X."
    r = rows[0]
    return (
        "ð¨ CRYPTO ALERT\n\n"
        f"{r['symbol']} {r['change']:+.2f}%\n"
        "Detected by AlphaRadar scanner.\n\n"
        "Free signals:\n"
        "t.me/alpharadar\n\n"
        "#Crypto #Trading #Binance"
    )


@bot.message_handler(commands=["start"])
def cmd_start(message):
    bot.reply_to(
        message,
        "AlphaRadar Final 1.0\n\n"
        "/pulse\n/top\n/ai\n/alerts\n/futures\n/trial\n/vip\n/payment\n/tweet"
    )


@bot.message_handler(commands=["pulse"])
def cmd_pulse(message):
    bot.reply_to(message, build_free_pulse())


@bot.message_handler(commands=["top"])
def cmd_top(message):
    bot.reply_to(message, build_top_movers())


@bot.message_handler(commands=["ai"])
def cmd_ai(message):
    bot.reply_to(message, build_ai_ranking() or "Brak AI ranking teraz.")


@bot.message_handler(commands=["alerts"])
def cmd_alerts(message):
    bot.reply_to(message, build_dex_alert() or "Brak alertow teraz.")


@bot.message_handler(commands=["futures"])
def cmd_futures(message):
    bot.reply_to(message, build_futures_alert() or "Brak futures alerts teraz.")


@bot.message_handler(commands=["trial"])
def cmd_trial(message):
    bot.reply_to(
        message,
        "ð Trial VIP aktywowany na 24h\n\n"
        "Masz dostep do:\n"
        "â¢ AI pump alerts\n"
        "â¢ whale activity\n"
        "â¢ smart money alerts\n"
        "â¢ futures momentum\n\n"
        "Pelny dostep -> /vip"
    )


@bot.message_handler(commands=["vip"])
def cmd_vip(message):
    bot.reply_to(
        message,
        f"AlphaRadar VIP\n\nCena: ${PRICE_USD}/month\n\n"
        "Co dostajesz:\n"
        "â¢ AI pump detection\n"
        "â¢ smart money alerts\n"
        "â¢ whale activity\n"
        "â¢ futures momentum\n"
        "â¢ DEX early tokens\n"
        "â¢ AI ranking\n\n"
        "/payment"
    )


@bot.message_handler(commands=["payment"])
def cmd_payment(message):
    bot.reply_to(
        message,
        f"Payment: {PAYMENT_INFO}\n\nUSDT TRC20:\n{USDT_TRC20_ADDRESS}"
    )


@bot.message_handler(commands=["tweet"])
def cmd_tweet(message):
    bot.reply_to(message, build_tweet())


def run_scheduler():
    while True:
        try:
            if should_run("free_pulse", FREE_PULSE_INTERVAL_MIN):
                safe_send(FREE_CHANNEL, build_free_pulse(), "free_pulse")

            if should_run("free_hype", FREE_HYPE_INTERVAL_MIN):
                safe_send(FREE_CHANNEL, build_free_hype(), "free_hype")

            if should_run("free_invite", FREE_INVITE_INTERVAL_MIN):
                safe_send(FREE_CHANNEL, build_free_invite(), "free_invite")

            if should_run("vip_top", VIP_TOP_INTERVAL_MIN):
                safe_send(VIP_CHANNEL, build_top_movers(), "vip_top")

            if should_run("vip_ai", VIP_AI_INTERVAL_MIN):
                txt = build_ai_ranking()
                if txt:
                    safe_send(VIP_CHANNEL, txt, "vip_ai")

            if should_run("vip_dex", VIP_DEX_INTERVAL_MIN):
                txt = build_dex_alert()
                if txt:
                    safe_send(VIP_CHANNEL, txt, "vip_dex")

            if should_run("vip_futures", VIP_FUTURES_INTERVAL_MIN):
                txt = build_futures_alert()
                if txt:
                    safe_send(VIP_CHANNEL, txt, "vip_futures")

        except Exception as e:
            print("scheduler error:", e)

        time.sleep(60)


if __name__ == "__main__":
    print("AlphaRadar Final 1.0 running")
    threading.Thread(target=run_scheduler, daemon=True).start()

    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print("BOT ERROR:", e)
            time.sleep(10)
