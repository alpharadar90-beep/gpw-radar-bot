# -*- coding: utf-8 -*-
import time
import schedule
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import telebot
import yfinance as yf
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8514506509:AAFDIZKCDuDN9sWwW-hMgX3xTP9_HyQGfG0"
ADMIN_ID = 123456789
FREE_CHANNEL = "@gpwradar"
PRO_CHANNEL = "@gpwradarpro"

PRICE_PLN = 99
PAYMENT_INFO = "BLIK / przelew / kontakt prywatny"

MORNING_BRIEF_HOUR = 8
MORNING_BRIEF_MINUTE = 45
MARKET_PULSE_INTERVAL_MIN = 30
MARKET_CLOSE_HOUR = 17
MARKET_CLOSE_MINUTE = 10

ALERT_MOVE_PCT = 3.0
ALERT_DROP_PCT = -3.0
ALERT_VOLUME_SPIKE = 2.0
RELATIVE_STRENGTH_THRESHOLD = 1.5
FREE_MARKETING_INTERVAL_MIN = 180

GPW_WATCHLIST: Dict[str, str] = {
    "KGH.WA": "KGHM", "PKN.WA": "Orlen", "PKO.WA": "PKO BP", "CDR.WA": "CD Projekt",
    "PZU.WA": "PZU", "PEO.WA": "Pekao", "ALE.WA": "Allegro", "PGE.WA": "PGE",
    "DNP.WA": "Dino", "XTB.WA": "XTB", "LPP.WA": "LPP", "JSW.WA": "JSW",
    "ACP.WA": "Asseco Poland", "BDX.WA": "Budimex", "MBK.WA": "mBank", "MIL.WA": "Millennium",
    "TPE.WA": "Tauron", "SPL.WA": "Santander PL", "ING.WA": "ING BSK", "ATT.WA": "Grupa Azoty",
    "TEN.WA": "Ten Square Games", "11B.WA": "11 bit studios", "KTY.WA": "Kety", "WPL.WA": "Wirtualna Polska",
}
SECTOR_MAP: Dict[str, str] = {
    "KGH.WA": "Materials", "PKN.WA": "Energy", "PKO.WA": "Banks", "CDR.WA": "Gaming",
    "PZU.WA": "Finance", "PEO.WA": "Banks", "ALE.WA": "Retail", "PGE.WA": "Utilities",
    "DNP.WA": "Retail", "XTB.WA": "Finance", "LPP.WA": "Retail", "JSW.WA": "Materials",
    "ACP.WA": "Technology", "BDX.WA": "Construction", "MBK.WA": "Banks", "MIL.WA": "Banks",
    "TPE.WA": "Utilities", "SPL.WA": "Banks", "ING.WA": "Banks", "ATT.WA": "Chemicals",
    "TEN.WA": "Gaming", "11B.WA": "Gaming", "KTY.WA": "Industrial", "WPL.WA": "Technology",
}
MACRO_SYMBOLS: Dict[str, str] = {
    "GC=F": "Gold", "SI=F": "Silver", "CL=F": "Oil", "NG=F": "Natural Gas", "CC=F": "Cocoa",
    "^GSPC": "S&P 500", "^IXIC": "NASDAQ", "^FTSE": "FTSE 100", "^GDAXI": "DAX",
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "EURPLN=X": "EUR/PLN", "USDPLN=X": "USD/PLN",
    "USDJPY=X": "USD/JPY", "BTC-USD": "Bitcoin",
}
WIG20_SYMBOL = "WIG20.WA"

bot = telebot.TeleBot(TOKEN, parse_mode=None)

def now_label() -> str:
    return datetime.now().strftime("%H:%M")

def safe_history(symbol: str, period: str = "5d", interval: str = "1d"):
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
        return None if df is None or df.empty else df
    except Exception:
        return None

def get_last_price(symbol: str) -> Optional[float]:
    df = safe_history(symbol)
    try:
        return None if df is None else float(df["Close"].iloc[-1])
    except Exception:
        return None

def get_daily_change_pct(symbol: str) -> Optional[float]:
    df = safe_history(symbol)
    if df is None or len(df) < 2:
        return None
    try:
        prev_close = float(df["Close"].iloc[-2]); last_close = float(df["Close"].iloc[-1])
        return None if prev_close == 0 else round((last_close / prev_close - 1) * 100, 2)
    except Exception:
        return None

def get_period_change_pct(symbol: str, days_back: int = 5) -> Optional[float]:
    df = safe_history(symbol, period=f"{days_back + 10}d")
    if df is None or len(df) < days_back + 1:
        return None
    try:
        prev = float(df["Close"].iloc[-(days_back + 1)]); last = float(df["Close"].iloc[-1])
        return None if prev == 0 else round((last / prev - 1) * 100, 2)
    except Exception:
        return None

def get_volume_spike_ratio(symbol: str) -> Optional[float]:
    df = safe_history(symbol, period="7d")
    if df is None or len(df) < 3:
        return None
    try:
        prev_vol = float(df["Volume"].iloc[-2]); last_vol = float(df["Volume"].iloc[-1])
        return None if prev_vol <= 0 else round(last_vol / prev_vol, 2)
    except Exception:
        return None

def get_momentum_3d(symbol: str) -> Optional[float]:
    df = safe_history(symbol, period="10d")
    if df is None or len(df) < 4:
        return None
    try:
        prev = float(df["Close"].iloc[-4]); last = float(df["Close"].iloc[-1])
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
    if symbol.endswith(".WA"): return f"{price:.2f} PLN"
    if symbol.endswith("=X"): return f"{price:.4f}"
    if symbol.startswith("^"): return f"{price:.2f}"
    return f"${price:.2f}"

def safe_send(target: str, text: str, label: str) -> None:
    try:
        bot.send_message(FREE_CHANNEL if target == "free" else PRO_CHANNEL, text)
    except Exception as e:
        print(f"{label} error: {e}")

def build_cta() -> str:
    return "\n\nMarkets PRO\nCena: {} PLN / miesiac\nMore signals -> @gpwradarpro\n/vip".format(PRICE_PLN)

def compose_message(title: str, lines: List[str], add_cta: bool = True) -> str:
    body = "\n".join([x for x in lines if x]).strip()
    msg = f"{title} ({now_label()})\n\n{body}"
    if add_cta: msg += build_cta()
    return msg

def compose_free_message(title: str, lines: List[str]) -> str:
    body = "\n".join([x for x in lines if x]).strip()
    return f"{title} ({now_label()})\n\n{body}\n\nMore signals -> @gpwradarpro"

def gpw_rows() -> List[Tuple[str, str, float, float]]:
    out = []
    for symbol, name in GPW_WATCHLIST.items():
        price = get_last_price(symbol); change = get_daily_change_pct(symbol)
        if price is not None and change is not None:
            out.append((symbol, name, change, price))
    return out

def top_gainers(limit: int = 10):
    rows = gpw_rows(); rows.sort(key=lambda x: x[2], reverse=True); return rows[:limit]

def top_losers(limit: int = 10):
    rows = gpw_rows(); rows.sort(key=lambda x: x[2]); return rows[:limit]

def momentum_rows(limit: int = 8):
    rows = []
    for symbol, name in GPW_WATCHLIST.items():
        mom = get_momentum_3d(symbol); price = get_last_price(symbol)
        if mom is not None and price is not None: rows.append((symbol, name, mom, price))
    rows.sort(key=lambda x: x[2], reverse=True); return rows[:limit]

def volume_spikes(limit: int = 8, threshold: float = ALERT_VOLUME_SPIKE):
    rows = []
    for symbol, name in GPW_WATCHLIST.items():
        ratio = get_volume_spike_ratio(symbol); price = get_last_price(symbol)
        if ratio is not None and price is not None: rows.append((symbol, name, ratio, price))
    rows = [r for r in rows if r[2] >= threshold]; rows.sort(key=lambda x: x[2], reverse=True); return rows[:limit]

def macro_rows(limit: int = 10):
    rows = []
    for symbol, name in MACRO_SYMBOLS.items():
        price = get_last_price(symbol); change = get_daily_change_pct(symbol)
        if price is not None and change is not None: rows.append((symbol, name, change, price))
    rows.sort(key=lambda x: abs(x[2]), reverse=True); return rows[:limit]

def sector_strength():
    buckets: Dict[str, List[float]] = {}
    for symbol, _, change, _ in gpw_rows():
        buckets.setdefault(SECTOR_MAP.get(symbol, "Other"), []).append(change)
    out = [(sector, round(sum(vals) / len(vals), 2)) for sector, vals in buckets.items()]
    out.sort(key=lambda x: x[1], reverse=True); return out

def market_score():
    rows = gpw_rows()
    if not rows: return 0, "Brak danych"
    positives = sum(1 for _, _, c, _ in rows if c > 0); negatives = sum(1 for _, _, c, _ in rows if c < 0)
    avg = sum(c for _, _, c, _ in rows) / len(rows)
    top = top_gainers(3); top_score = sum(1 for _, _, c, _ in top if c > 2)
    score = 5 + (1 if positives > negatives else -1) + (1 if avg > 0.5 else (-1 if avg < -0.5 else 0)) + (1 if top_score >= 2 else 0)
    score = max(0, min(10, score))
    label = "Strong" if score >= 8 else "Constructive" if score >= 6 else "Mixed" if score >= 4 else "Weak"
    return score, label

def relative_strength_rows(limit: int = 8):
    wig_change = get_daily_change_pct(WIG20_SYMBOL)
    if wig_change is None: return []
    rows = []
    for symbol, name in GPW_WATCHLIST.items():
        ch = get_daily_change_pct(symbol); price = get_last_price(symbol)
        if ch is not None and price is not None:
            rs = round(ch - wig_change, 2)
            if abs(rs) >= RELATIVE_STRENGTH_THRESHOLD: rows.append((symbol, name, rs, ch, price))
    rows.sort(key=lambda x: x[2], reverse=True); return rows[:limit]

def breakouts(limit: int = 8):
    out = []
    for symbol, name in GPW_WATCHLIST.items():
        price = get_last_price(symbol); change = get_daily_change_pct(symbol)
        if price is None or change is None: continue
        if is_new_high(symbol, 20): out.append(f"{name} | NEW 20D HIGH | {fmt_price(symbol, price)} | {change:+.2f}%")
        elif is_new_low(symbol, 20): out.append(f"{name} | NEW 20D LOW | {fmt_price(symbol, price)} | {change:+.2f}%")
    return out[:limit]

def move_alerts(limit: int = 8):
    out = []
    for symbol, name, change, price in gpw_rows():
        ratio = get_volume_spike_ratio(symbol) or 1.0
        if change >= ALERT_MOVE_PCT or change <= ALERT_DROP_PCT:
            out.append(f"{name} | {fmt_price(symbol, price)} | {change:+.2f}% | Vol x{ratio:.2f}")
    return out[:limit]

def crash_detector(limit: int = 6):
    out = []
    for symbol, name, change, price in gpw_rows():
        ratio = get_volume_spike_ratio(symbol) or 1.0
        if change <= -4.0 and ratio >= 1.2:
            out.append(f"{name} | {fmt_price(symbol, price)} | {change:+.2f}% | Vol x{ratio:.2f}")
    return out[:limit]

def early_breakouts(limit: int = 6):
    items = []
    for symbol, name in GPW_WATCHLIST.items():
        mom = get_momentum_3d(symbol); ratio = get_volume_spike_ratio(symbol)
        price = get_last_price(symbol); change = get_daily_change_pct(symbol)
        if None in (mom, ratio, price, change): continue
        if mom >= 2.0 and ratio >= 1.5 and 0 < change < 5:
            items.append((name, mom, ratio, price, change))
    items.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return [f"{name} | {change:+.2f}% | Mom {mom:+.2f}% | Vol x{ratio:.2f} | {price:.2f} PLN" for name, mom, ratio, price, change in items[:limit]]

def top_volume_ranking(limit: int = 8):
    rows = []
    for symbol, name in GPW_WATCHLIST.items():
        ratio = get_volume_spike_ratio(symbol); ch = get_daily_change_pct(symbol); price = get_last_price(symbol)
        if None not in (ratio, ch, price): rows.append((name, ratio, ch, price))
    rows.sort(key=lambda x: x[1], reverse=True)
    return [f"{name} | Vol x{ratio:.2f} | {ch:+.2f}% | {price:.2f} PLN" for name, ratio, ch, price in rows[:limit]]

def weekly_winners(limit: int = 8):
    rows = []
    for symbol, name in GPW_WATCHLIST.items():
        ch = get_period_change_pct(symbol, 5)
        if ch is not None: rows.append((name, ch))
    rows.sort(key=lambda x: x[1], reverse=True)
    return [f"{name} | {change:+.2f}%" for name, change in rows[:limit]]

def daily_stats_lines():
    rows = gpw_rows()
    up = sum(1 for _, _, c, _ in rows if c > 0); down = sum(1 for _, _, c, _ in rows if c < 0); flat = len(rows) - up - down
    best = top_gainers(1); worst = top_losers(1); score, label = market_score()
    lines = [f"Advancers: {up}", f"Decliners: {down}", f"Flat: {flat}", f"Market Strength Score: {score}/10 ({label})"]
    if best: lines.append(f"Best of day: {best[0][1]} {best[0][2]:+.2f}%")
    if worst: lines.append(f"Worst of day: {worst[0][1]} {worst[0][2]:+.2f}%")
    return lines

def ai_market_insight_lines():
    rows = gpw_rows()
    if not rows: return ["Brak danych rynkowych teraz."]
    score, label = market_score(); heat = sector_strength(); gainers = top_gainers(3); losers = top_losers(3); spikes = volume_spikes(3, 1.5); momentum = momentum_rows(3); rs = relative_strength_rows(3)
    lines = [f"Market regime: {label} ({score}/10)"]
    if heat:
        lines.append(f"Leader sector: {heat[0][0]} {heat[0][1]:+.2f}%"); lines.append(f"Weakest sector: {heat[-1][0]} {heat[-1][1]:+.2f}%")
    if gainers:
        lines.append("Leaders:"); lines += [f"- {name} {change:+.2f}%" for _, name, change, _ in gainers]
    if losers:
        lines.append("Lagging names:"); lines += [f"- {name} {change:+.2f}%" for _, name, change, _ in losers]
    if spikes:
        lines.append("Volume focus:"); lines += [f"- {name} x{ratio:.2f}" for _, name, ratio, _ in spikes]
    if momentum:
        lines.append("Momentum focus:"); lines += [f"- {name} {mom:+.2f}%" for _, name, mom, _ in momentum]
    if rs:
        lines.append("Relative strength vs WIG20:"); lines += [f"- {name} RS {rsv:+.2f}pp" for _, name, rsv, _, _ in rs]
    lines.append("AI view: Bias bullish, focus on strength and breakouts." if score >= 7 else "AI view: Bias defensive, avoid chasing weak names." if score <= 3 else "AI view: Mixed tape, prefer selective setups only.")
    return lines

def build_free_market_pulse(): return compose_free_message("MARKET PULSE", ["GPW"] + [f"{n} {c:+.2f}%" for _, n, c, _ in top_gainers(3)] + ["", "Macro"] + [f"{n} {c:+.2f}%" for _, n, c, _ in macro_rows(3)])
def build_free_top_gainers(): return compose_free_message("Top Gainers", [f"{n} | {c:+.2f}% | {fmt_price(s, p)}" for s, n, c, p in top_gainers(5)])
def build_free_top_losers(): return compose_free_message("Top Losers", [f"{n} | {c:+.2f}% | {fmt_price(s, p)}" for s, n, c, p in top_losers(5)])
def build_free_macro(): return compose_free_message("MACRO RADAR", [f"{n} | {fmt_price(s, p)} | {c:+.2f}%" for s, n, c, p in macro_rows(6)])
def build_free_volume_spike():
    rows = volume_spikes(3)
    return None if not rows else compose_free_message("VOLUME SPIKE", [f"{n} | x{r:.2f} | {fmt_price(s, p)}" for s, n, r, p in rows])
def build_free_alert():
    alerts = move_alerts(1)
    return None if not alerts else compose_free_message("GPW ALERT", alerts)
def build_free_marketing_post():
    score, label = market_score(); gainers = top_gainers(2)
    lines = [f"Market Strength Score: {score}/10 ({label})"] + [f"{n} {c:+.2f}%" for _, n, c, _ in gainers] + ["", "Full signals -> @gpwradarpro"]
    return compose_free_message("FREE -> PRO", lines)

def build_gpw_update(): return compose_message("GPW Update", [f"{n} | {fmt_price(s, p)} | {c:+.2f}%" for s, n, c, p in top_gainers(12)])
def build_market_pulse():
    score, label = market_score()
    lines = ["GPW"] + [f"{n} {c:+.2f}%" for _, n, c, _ in top_gainers(3)] + ["", "Momentum"] + [f"{n} {m:+.2f}%" for _, n, m, _ in momentum_rows(3)] + ["", "Macro"] + [f"{n} {c:+.2f}%" for _, n, c, _ in macro_rows(3)] + ["", f"Market Strength Score: {score}/10 ({label})"]
    return compose_message("MARKET PULSE", lines)
def build_top_gainers(): return compose_message("Top Gainers", [f"{n} | {c:+.2f}% | {fmt_price(s, p)}" for s, n, c, p in top_gainers(10)])
def build_top_losers(): return compose_message("Top Losers", [f"{n} | {c:+.2f}% | {fmt_price(s, p)}" for s, n, c, p in top_losers(10)])
def build_volume_spike():
    rows = volume_spikes(8)
    return None if not rows else compose_message("Volume Spike", [f"{n} | x{r:.2f} | {fmt_price(s, p)}" for s, n, r, p in rows])
def build_macro_radar(): return compose_message("Macro Radar", [f"{n} | {fmt_price(s, p)} | {c:+.2f}%" for s, n, c, p in macro_rows(12)])
def build_global_radar(): return compose_message("Global Radar", [f"{n} | {fmt_price(s, p)} | {c:+.2f}%" for s, n, c, p in macro_rows(8)])
def build_morning_brief():
    score, label = market_score(); heat = sector_strength()[:3]
    lines = ["GPW focus"] + [f"{n} | {fmt_price(s, p)} | {c:+.2f}%" for s, n, c, p in top_gainers(5)] + ["", "Macro focus"] + [f"{n} | {fmt_price(s, p)} | {c:+.2f}%" for s, n, c, p in macro_rows(5)] + ["", "Sector heatmap"] + [f"{sec} | {strn:+.2f}%" for sec, strn in heat] + ["", f"Market Strength Score: {score}/10 ({label})"]
    return compose_message("Morning Brief", lines)
def build_market_close():
    lines = ["Top day gainers"] + [f"{n} | {c:+.2f}%" for _, n, c, _ in top_gainers(5)] + ["", "Top day losers"] + [f"{n} | {c:+.2f}%" for _, n, c, _ in top_losers(5)] + [""] + daily_stats_lines()
    return compose_message("MARKET CLOSE", lines)
def build_pro_signal_pack():
    rows = []
    for symbol, name in GPW_WATCHLIST.items():
        mom = get_momentum_3d(symbol); ratio = get_volume_spike_ratio(symbol); price = get_last_price(symbol); change = get_daily_change_pct(symbol)
        if None in (mom, ratio, price, change): continue
        score = mom * 0.7 + ratio * 1.5 + change * 0.5; rows.append((symbol, name, mom, ratio, price, change, score))
    rows = [r for r in rows if r[2] > 0 and r[3] >= 1.1]; rows.sort(key=lambda x: x[6], reverse=True)
    if not rows: return compose_message("PRO Signal Pack", ["Brak mocnych sygnalow teraz."])
    lines = []
    for s, n, m, r, p, c, _ in rows[:6]:
        lines += [n, f"Change: {c:+.2f}%", f"Momentum: {m:+.2f}%", f"Volume: x{r:.2f}", f"Cena: {fmt_price(s, p)}", ""]
    return compose_message("PRO Signal Pack", lines)
def build_heatmap(): return compose_message("GPW Heatmap", [f"{sec} | {strn:+.2f}%" for sec, strn in sector_strength()])
def build_breakouts(): return compose_message("Breakouts", breakouts() or ["Brak nowych 20D high/low teraz."])
def build_move_alerts():
    lines = move_alerts()
    return None if not lines else compose_message("Move Alerts", lines)
def build_daily_stats(): return compose_message("Daily Stats", daily_stats_lines())
def build_weekly_winners(): return compose_message("Weekly Winners", weekly_winners())
def build_ai_insight(): return compose_message("AI Market Insight", ai_market_insight_lines())
def build_relative_strength():
    rows = relative_strength_rows()
    return compose_message("Relative Strength vs WIG20", ["Brak wyraznej przewagi teraz."] if not rows else [f"{n} | RS {rs:+.2f}pp | {c:+.2f}% | {fmt_price(s, p)}" for s, n, rs, c, p in rows])
def build_early_breakout(): return compose_message("Early Breakout Detector", early_breakouts() or ["Brak wczesnych breakoutow teraz."])
def build_crash_detector(): return compose_message("Crash Detector", crash_detector() or ["Brak crash alertow teraz."])
def build_top_volume(): return compose_message("Top Volume Ranking", top_volume_ranking())

def daily_market_brief_lines():
    score, label = market_score()
    heat = sector_strength()[:4]
    gain = top_gainers(4)
    lose = top_losers(4)
    macro = macro_rows(5)
    lines = [f"Market Strength: {score}/10 ({label})", "", "Top Gainers"]
    lines += [f"- {name} {chg:+.2f}%" for _, name, chg, _ in gain]
    lines += ["", "Top Losers"]
    lines += [f"- {name} {chg:+.2f}%" for _, name, chg, _ in lose]
    lines += ["", "Sector Heatmap"]
    lines += [f"- {sec} {val:+.2f}%" for sec, val in heat]
    lines += ["", "Macro Focus"]
    lines += [f"- {name} {chg:+.2f}%" for _, name, chg, _ in macro]
    return lines

def smart_money_flow_lines(limit: int = 6):
    items = []
    for symbol, name in GPW_WATCHLIST.items():
        ratio = get_volume_spike_ratio(symbol)
        chg = get_daily_change_pct(symbol)
        price = get_last_price(symbol)
        if None in (ratio, chg, price):
            continue
        flow = round((ratio * 2.0) + max(chg, 0), 2)
        if ratio >= 1.8 and chg > 0:
            items.append((name, flow, ratio, chg, price))
    items.sort(key=lambda x: x[1], reverse=True)
    return [f"{name} | Flow {flow:.2f} | Vol x{ratio:.2f} | {chg:+.2f}% | {price:.2f} PLN" for name, flow, ratio, chg, price in items[:limit]]

def ai_signal_score_lines(limit: int = 6):
    items = []
    wig = get_daily_change_pct(WIG20_SYMBOL) or 0.0
    for symbol, name in GPW_WATCHLIST.items():
        chg = get_daily_change_pct(symbol)
        mom = get_momentum_3d(symbol)
        vol = get_volume_spike_ratio(symbol)
        price = get_last_price(symbol)
        if None in (chg, mom, vol, price):
            continue
        rs = chg - wig
        score = max(0, min(10, round((chg * 0.8) + (mom * 0.6) + (vol * 1.2) + (rs * 0.4), 2)))
        items.append((name, score, chg, mom, vol, price))
    items.sort(key=lambda x: x[1], reverse=True)
    return [f"{name} | Score {score:.2f}/10 | {chg:+.2f}% | Mom {mom:+.2f}% | Vol x{vol:.2f} | {price:.2f} PLN" for name, score, chg, mom, vol, price in items[:limit]]

def build_daily_market_brief():
    return compose_message("Daily Market Brief", daily_market_brief_lines())

def build_smart_money_flow():
    lines = smart_money_flow_lines()
    if not lines:
        lines = ["Brak wyraznego smart money teraz."]
    return compose_message("Smart Money Flow", lines)

def build_ai_signal_score():
    lines = ai_signal_score_lines()
    if not lines:
        lines = ["Brak sygnalow scoringowych teraz."]
    return compose_message("AI Signal Score", lines)

def vip_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Kup PRO", callback_data="vip_buy"))
    kb.add(InlineKeyboardButton("Platnosc", callback_data="vip_payment"))
    return kb

@bot.callback_query_handler(func=lambda call: True)
def cb_handler(call):
    if call.data == "vip_buy": bot.answer_callback_query(call.id, "Napisz prywatnie po aktywacje PRO.")
    elif call.data == "vip_payment": bot.answer_callback_query(call.id, PAYMENT_INFO)

@bot.message_handler(commands=["start"])
def cmd_start(message):
    text = "GPW Radar PRO8\n\nKomendy:\n/gpw\n/pulse\n/gainers\n/losers\n/volume\n/momentum\n/macro\n/global\n/heatmap\n/breakouts\n/alerts\n/stats\n/weekly\n/prosignals\n/ai\n/rs\n/early\n/crash\n/topvolume\n/brief\n/smartmoney\n/aiscore\n/vip\n/payment"
    bot.reply_to(message, text, reply_markup=vip_keyboard())

@bot.message_handler(commands=["gpw"])
def cmd_gpw(message): bot.reply_to(message, build_gpw_update())
@bot.message_handler(commands=["pulse", "market"])
def cmd_pulse(message): bot.reply_to(message, build_market_pulse())
@bot.message_handler(commands=["gainers"])
def cmd_gainers(message): bot.reply_to(message, build_top_gainers())
@bot.message_handler(commands=["losers"])
def cmd_losers(message): bot.reply_to(message, build_top_losers())
@bot.message_handler(commands=["volume"])
def cmd_volume(message): bot.reply_to(message, build_volume_spike() or "Brak wyraznych spike'ow wolumenu teraz.")
@bot.message_handler(commands=["momentum"])
def cmd_momentum(message):
    rows = momentum_rows(8)
    bot.reply_to(message, compose_message("Momentum", [f"{n} | {m:+.2f}% | {fmt_price(s, p)}" for s, n, m, p in rows]))
@bot.message_handler(commands=["macro"])
def cmd_macro(message): bot.reply_to(message, build_macro_radar())
@bot.message_handler(commands=["global"])
def cmd_global(message): bot.reply_to(message, build_global_radar())
@bot.message_handler(commands=["heatmap"])
def cmd_heatmap(message): bot.reply_to(message, build_heatmap())
@bot.message_handler(commands=["breakouts"])
def cmd_breakouts(message): bot.reply_to(message, build_breakouts())
@bot.message_handler(commands=["alerts"])
def cmd_alerts(message): bot.reply_to(message, build_move_alerts() or "Brak ruchow powyzej progow alertu.")
@bot.message_handler(commands=["stats"])
def cmd_stats(message): bot.reply_to(message, build_daily_stats())
@bot.message_handler(commands=["weekly"])
def cmd_weekly(message): bot.reply_to(message, build_weekly_winners())
@bot.message_handler(commands=["prosignals"])
def cmd_prosignals(message): bot.reply_to(message, build_pro_signal_pack())
@bot.message_handler(commands=["ai"])
def cmd_ai(message): bot.reply_to(message, build_ai_insight())
@bot.message_handler(commands=["rs"])
def cmd_rs(message): bot.reply_to(message, build_relative_strength())
@bot.message_handler(commands=["early"])
def cmd_early(message): bot.reply_to(message, build_early_breakout())
@bot.message_handler(commands=["crash"])
def cmd_crash(message): bot.reply_to(message, build_crash_detector())
@bot.message_handler(commands=["topvolume"])
def cmd_topvolume(message): bot.reply_to(message, build_top_volume())
@bot.message_handler(commands=["brief"])
def cmd_brief(message): bot.reply_to(message, build_daily_market_brief())

@bot.message_handler(commands=["smartmoney"])
def cmd_smartmoney(message): bot.reply_to(message, build_smart_money_flow())

@bot.message_handler(commands=["aiscore"])
def cmd_aiscore(message): bot.reply_to(message, build_ai_signal_score())

@bot.message_handler(commands=["vip"])
def cmd_vip(message):
    bot.reply_to(message, f"Markets PRO\nCena: {PRICE_PLN} PLN / miesiac\n\nCo dostajesz:\n- GPW Update\n- Top Gainers / Losers\n- Volume Spike\n- Momentum\n- Macro / Global Radar\n- Heatmap\n- Breakouts\n- Move Alerts\n- Daily Stats\n- Weekly Winners\n- PRO Signal Pack\n- AI Insight\n- Relative Strength vs WIG20\n- Early Breakout Detector\n- Crash Detector\n- Top Volume Ranking\n- Daily Market Brief\n- Smart Money Flow\n- AI Signal Score\n\n/payment", reply_markup=vip_keyboard())
@bot.message_handler(commands=["payment"])
def cmd_payment(message): bot.reply_to(message, f"Platnosc: {PAYMENT_INFO}")

def run_every(minutes: int, fn, label: str):
    while True:
        try: fn()
        except Exception as e: print(f"{label} error: {e}")
        time.sleep(minutes * 60)

def run_daily(hour: int, minute: int, fn, label: str):
    last_stamp = None
    while True:
        try:
            now = datetime.now(); stamp = now.strftime("%Y-%m-%d %H:%M")
            if now.hour == hour and now.minute == minute and stamp != last_stamp:
                fn(); last_stamp = stamp
        except Exception as e:
            print(f"{label} error: {e}")
        time.sleep(20)

def auto_free_pulse(): safe_send("free", build_free_market_pulse(), "free_pulse")
def auto_free_gainers(): safe_send("free", build_free_top_gainers(), "free_gainers")
def auto_free_losers(): safe_send("free", build_free_top_losers(), "free_losers")
def auto_free_macro(): safe_send("free", build_free_macro(), "free_macro")
def auto_free_volume():
    txt = build_free_volume_spike()
    if txt: safe_send("free", txt, "free_volume")
def auto_free_alert():
    txt = build_free_alert()
    if txt: safe_send("free", txt, "free_alert")
def auto_free_marketing(): safe_send("free", build_free_marketing_post(), "free_marketing")

def auto_market_pulse(): safe_send("pro", build_market_pulse(), "pulse")
def auto_gpw_update(): safe_send("pro", build_gpw_update(), "gpw")
def auto_top_gainers(): safe_send("pro", build_top_gainers(), "gainers")
def auto_top_losers(): safe_send("pro", build_top_losers(), "losers")
def auto_volume_spike():
    txt = build_volume_spike()
    if txt: safe_send("pro", txt, "volume")
def auto_macro_radar(): safe_send("pro", build_macro_radar(), "macro")
def auto_global_radar(): safe_send("pro", build_global_radar(), "global")
def auto_heatmap(): safe_send("pro", build_heatmap(), "heatmap")
def auto_breakouts(): safe_send("pro", build_breakouts(), "breakouts")
def auto_move_alerts():
    txt = build_move_alerts()
    if txt: safe_send("pro", txt, "alerts")
def auto_morning_brief(): safe_send("pro", build_morning_brief(), "morning")
def auto_market_close(): safe_send("pro", build_market_close(), "close")
def auto_prosignals(): safe_send("pro", build_pro_signal_pack(), "prosignals")
def auto_daily_stats(): safe_send("pro", build_daily_stats(), "stats")
def auto_ai_insight(): safe_send("pro", build_ai_insight(), "ai")
def auto_relative_strength(): safe_send("pro", build_relative_strength(), "rs")
def auto_early_breakout(): safe_send("pro", build_early_breakout(), "early")
def auto_crash_detector(): safe_send("pro", build_crash_detector(), "crash")
def auto_top_volume(): safe_send("pro", build_top_volume(), "topvolume")

def auto_daily_market_brief(): safe_send("pro", build_daily_market_brief(), "brief")
def auto_smart_money_flow(): safe_send("pro", build_smart_money_flow(), "smartmoney")
def auto_ai_signal_score(): safe_send("pro", build_ai_signal_score(), "aiscore")

threading.Thread(target=run_every, args=(30, auto_free_pulse, "free_pulse_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(90, auto_free_gainers, "free_gainers_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(90, auto_free_losers, "free_losers_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(120, auto_free_macro, "free_macro_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(120, auto_free_volume, "free_volume_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(60, auto_free_alert, "free_alert_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(FREE_MARKETING_INTERVAL_MIN, auto_free_marketing, "free_marketing_thread"), daemon=True).start()

threading.Thread(target=run_every, args=(MARKET_PULSE_INTERVAL_MIN, auto_market_pulse, "pulse_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(60, auto_gpw_update, "gpw_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(120, auto_top_gainers, "gainers_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(120, auto_top_losers, "losers_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(90, auto_volume_spike, "volume_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(90, auto_macro_radar, "macro_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(120, auto_global_radar, "global_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(180, auto_heatmap, "heatmap_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(180, auto_breakouts, "breakouts_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(120, auto_move_alerts, "alerts_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(180, auto_prosignals, "prosignals_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(240, auto_ai_insight, "ai_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(180, auto_relative_strength, "rs_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(180, auto_early_breakout, "early_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(180, auto_crash_detector, "crash_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(180, auto_top_volume, "topvolume_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(240, auto_smart_money_flow, "smartmoney_thread"), daemon=True).start()
threading.Thread(target=run_every, args=(240, auto_ai_signal_score, "aiscore_thread"), daemon=True).start()
threading.Thread(target=run_daily, args=(MORNING_BRIEF_HOUR, MORNING_BRIEF_MINUTE + 1, auto_daily_market_brief, "brief_thread"), daemon=True).start()
threading.Thread(target=run_daily, args=(MORNING_BRIEF_HOUR, MORNING_BRIEF_MINUTE, auto_morning_brief, "morning_thread"), daemon=True).start()
threading.Thread(target=run_daily, args=(MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE, auto_market_close, "close_thread"), daemon=True).start()
threading.Thread(target=run_daily, args=(MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE + 1, auto_daily_stats, "stats_thread"), daemon=True).start()

while True:
    try:
        print("GPW & Markets PRO8 bot started...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("BOT ERROR:", e)
        print("Restart in 10 seconds...")
        time.sleep(10)
        # update
