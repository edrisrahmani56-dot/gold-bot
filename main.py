import yfinance as yf
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
import threading
import os

TELEGRAM_TOKEN = "  8932224201:AAFUYs0h5ZqFaY2zDR9EG5m3Abqf3Eedjas
" 
SYMBOL = "GC=F"
app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Bot is Alive!"
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

def get_data(interval, period):
    df = yf.download(SYMBOL, interval=interval, period=period, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()

def add_indicators(df):
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    tr = pd.concat([df["High"]-df["Low"], (df["High"]-df["Close"].shift()).abs(), (df["Low"]-df["Close"].shift()).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    return df

def trend_status(df):
    last = df.iloc[-1]
    if last["Close"] > last["EMA50"] and last["EMA20"] > last["EMA50"] and last["RSI"] > 50:
        return "BULLISH 🟢", last
    elif last["Close"] < last["EMA50"] and last["EMA20"] < last["EMA50"] and last["RSI"] < 50:
        return "BEARISH 🔴", last
    else:
        return "NEUTRAL ⚪", last

def analyze_gold():
    df_h4 = add_indicators(get_data("60m", "1mo").resample("4h").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna())
    df_h1 = add_indicators(get_data("60m", "5d"))
    df_m5 = add_indicators(get_data("5m", "2d"))
    trend_h4, last_h4 = trend_status(df_h4)
    trend_h1, last_h1 = trend_status(df_h1)
    last_m5 = df_m5.iloc[-1]; prev_m5 = df_m5.iloc[-2]
    price = float(last_m5["Close"]); atr_m5 = float(last_m5["ATR"]); rsi_m5 = float(last_m5["RSI"])
    signal = "WAIT"; sl=tp1=tp2=tp3=0; direction=""
    is_bull = "BULLISH" in trend_h4 and "BULLISH" in trend_h1
    is_bear = "BEARISH" in trend_h4 and "BEARISH" in trend_h1
    if is_bull and prev_m5["Close"] < prev_m5["EMA20"] and last_m5["Close"] > float(last_m5["EMA20"]) and rsi_m5 > 50:
        direction="BUY 🟢"; signal="BUY"; sl=price-(atr_m5*1.5); risk=price-sl; tp1=price+risk*1.5; tp2=price+risk*2.5; tp3=price+risk*3.5
    elif is_bear and prev_m5["Close"] > prev_m5["EMA20"] and last_m5["Close"] < float(last_m5["EMA20"]) and rsi_m5 < 50:
        direction="SELL 🔴"; signal="SELL"; sl=price+(atr_m5*1.5); risk=sl-price; tp1=price-risk*1.5; tp2=price-risk*2.5; tp3=price-risk*3.5
    msg=f"💰 تحلیل طلا XAU/USD\n\nH4: {trend_h4} | {float(last_h4['Close']):.2f}\nH1: {trend_h1} | {float(last_h1['Close']):.2f}\nM5: {price:.2f} | RSI: {rsi_m5:.1f}\n"
    if signal in ["BUY","SELL"]:
        msg+=f"\n✅ سیگنال: {direction}\n🎯 ورود: {price:.2f}\n🛑 ضرر: {sl:.2f}\n💰 سود۱: {tp1:.2f}\n💰 سود۲: {tp2:.2f}\n💰 سود۳: {tp3:.2f}\n"
    else:
        msg+=f"\n⏳ فعلا ورود نده!\nقیمت فعلی: {price:.2f}\n"
    return msg+"📌 آموزشی است."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! ربات ۲۴ ساعته روشنه 💹\nبزن: /analyze")
async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ در حال تحلیل...")
    try:
        await update.message.reply_text(analyze_gold())
    except Exception as e:
        await update.message.reply_text(f"خطا: {e}")

def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyze", analyze))
    app.run_polling()

threading.Thread(target=run_flask).start()
run_bot()
