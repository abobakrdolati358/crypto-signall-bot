import ccxt
import pandas as pd
import ta
import time
import schedule
import requests
import json
import os

# =============== تنظیمات ربات تلگرام ===============
TOKEN = "8128166184:AAGYipsvRkKXiyXIF2H1eIIjYM4hplU47P8"
CHAT_ID = "80150929"
TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
POSITION_FILE = "positions.json"

# =============== توابع تلگرام ===============
def send_telegram_message(text):
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(TELEGRAM_URL, data=payload)

# =============== مدیریت فایل پوزیشن‌ها ===============
def load_positions():
    if not os.path.exists(POSITION_FILE):
        with open(POSITION_FILE, "w") as f:
            json.dump({}, f)
    with open(POSITION_FILE, "r") as f:
        return json.load(f)

def save_positions(data):
    with open(POSITION_FILE, "w") as f:
        json.dump(data, f)

# =============== تابع تحلیل اصلی ===============
def analyze():
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [s for s in markets if s.endswith("/USDT") and ":" not in s]

    positions = load_positions()
    new_positions = positions.copy()
    message = ""

    for symbol in symbols:
        for timeframe in ["4h", "1d"]:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=200)
                df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
                df["ma50"] = df["close"].rolling(window=50).mean()
                df["ma200"] = df["close"].rolling(window=200).mean()

                latest = df.iloc[-1]
                key = f"{symbol}_{timeframe}"

                # سیگنال خرید
                if latest["rsi"] < 30 and latest["ma50"] > latest["ma200"]:
                    if key not in positions:
                        message += f"🟢 خرید: {symbol} | {timeframe} | RSI={latest['rsi']:.2f}\n"
                        new_positions[key] = "open"

                # سیگنال فروش
                if key in positions:
                    if latest["rsi"] > 70 or latest["ma50"] < latest["ma200"]:
                        message += f"🔴 فروش: {symbol} | {timeframe} | RSI={latest['rsi']:.2f}\n"
                        new_positions.pop(key)

            except Exception as e:
                print(f"⚠️ خطا در {symbol}: {e}")

    save_positions(new_positions)
    if message:
        send_telegram_message("📈 سیگنال‌ها:\n" + message)

# =============== زمان‌بندی اجرای خودکار ===============
schedule.every(4).hours.do(analyze)
schedule.every().day.at("09:00").do(analyze)

print("🤖 ربات در حال اجراست... (خرید و فروش در همه رمزارزهای USDT)")
while True:
    schedule.run_pending()
    time.sleep(60)
