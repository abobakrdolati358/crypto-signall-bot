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
                        entry_price = latest["close"]
                        message += f"🟢 خرید: {symbol} | {timeframe} | ورود: {entry_price:.4f} | RSI={latest['rsi']:.2f}\n"
                        new_positions[key] = {"status": "open", "entry_price": entry_price}

                # سیگنال فروش (یا بستن پوزیشن خرید)
                if key in positions and isinstance(positions[key], dict):
                    if latest["rsi"] > 70 or latest["ma50"] < latest["ma200"]:
                        entry_price = positions[key]["entry_price"]
                        exit_price = latest["close"]
                        growth = ((exit_price - entry_price) / entry_price) * 100
                        message += f"🔴 فروش: {symbol} | {timeframe} | خروج: {exit_price:.4f} | رشد: {growth:.2f}%\n"
                        new_positions.pop(key)

                # سیگنال شورت (فروش استقراضی)
                short_key = f"short_{symbol}_{timeframe}"
                if latest["rsi"] > 70 and latest["close"] > latest["ma50"] and latest["close"] < latest["ma200"]:
                    if short_key not in positions:
                        entry_price = latest["close"]
                        message += f"📉 شورت: {symbol} | {timeframe} | ورود: {entry_price:.4f} | RSI={latest['rsi']:.2f}\n"
                        new_positions[short_key] = {"status": "short", "entry_price": entry_price}

                if short_key in positions and isinstance(positions[short_key], dict):
                    if latest["rsi"] < 50:
                        entry_price = positions[short_key]["entry_price"]
                        exit_price = latest["close"]
                        drop = ((entry_price - exit_price) / entry_price) * 100
                        message += f"📈 بستن شورت: {symbol} | {timeframe} | خروج: {exit_price:.4f} | سود: {drop:.2f}%\n"
                        new_positions.pop(short_key)

            except Exception as e:
                print(f"⚠️ خطا در {symbol}: {e}")

    save_positions(new_positions)
    if message:
        send_telegram_message("📊 سیگنال‌ها:\n" + message)
