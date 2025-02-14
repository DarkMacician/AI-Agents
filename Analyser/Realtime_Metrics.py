import time
import requests
import threading
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta

# MongoDB Connection
uri = "mongodb+srv://prompt:123@cluster0.admu7.mongodb.net"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['Other_Information']
collection = db['Metrics']

# API Keys & URLs
LUNARCRUSH_KEY = "egisnd83jy9jda8j1zw61lh2tm73h6it7ll6c7n6"
BINANCE_API = "https://api4.binance.com/api/v3/ticker/24hr"
COINGECKO_API = "https://api.coingecko.com/api/v3/coins/"
TOKENS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]

# Last recorded data for delta calculations
last_liquidity = {}
last_holders = {}
last_mindshare = {}

def get_binance_data(symbol):
    """Fetches trading data from Binance API"""
    try:
        response = requests.get(BINANCE_API, params={"symbol": symbol}).json()
        return {
            "symbol": symbol.replace("USDT", ""),
            "liquidity": float(response.get("quoteVolume", 0)),
            "delta_liquidity": float(response.get("priceChangePercent", 0)),
        }
    except Exception as e:
        print(f"[ERROR] Binance API error for {symbol}: {e}")
        return {"symbol": symbol.replace("USDT", ""), "liquidity": 0, "delta_liquidity": 0}

def get_holders(symbol):
    """Fetches holders from CoinGecko"""
    coin_map = {"BNB": "binancecoin", "ADA": "cardano"}
    if symbol in coin_map:
        try:
            response = requests.get(f"{COINGECKO_API}{coin_map[symbol]}").json()
            return int(response.get("market_data", {}).get("circulating_supply", 0))
        except Exception as e:
            print(f"[ERROR] CoinGecko error for {symbol}: {e}")
    return 0

def get_mindshare(symbol):
    """Fetches mindshare from LunarCrush"""
    try:
        url = f"https://api.lunarcrush.com/v2?data=assets&key={LUNARCRUSH_KEY}&symbol={symbol}"
        response = requests.get(url).json()
        return float(response["data"][0]["social_dominance"])
    except Exception as e:
        print(f"[ERROR] LunarCrush error for {symbol}: {e}")
        return 0

def delete_old_data():
    """Deletes records older than 31 days from the database."""
    threshold_date = datetime.utcnow() - timedelta(days=31)
    result = collection.delete_many({"timestamp": {"$lt": threshold_date.strftime('%Y-%m-%d %H:%M')}})
    print(f"[INFO] Deleted {result.deleted_count} old records.")

def fetch_and_store_data(timestamp, symbol):
    """Fetches all metrics and saves them to MongoDB"""
    global last_liquidity, last_holders, last_mindshare

    binance_data = get_binance_data(symbol + "USDT")

    # Fetch holders
    holders = get_holders(symbol)
    delta_holders = holders - last_holders.get(symbol, holders)
    last_holders[symbol] = holders

    # Fetch mindshare & delta mindshare
    mindshare = get_mindshare(symbol)
    delta_mindshare = mindshare - last_mindshare.get(symbol, mindshare)
    last_mindshare[symbol] = mindshare

    # Compute echo (change in liquidity)
    liquidity = binance_data["liquidity"]
    delta_liquidity = binance_data["delta_liquidity"]
    echo = liquidity - last_liquidity.get(symbol, liquidity)
    last_liquidity[symbol] = liquidity

    # Store data
    data = {
        "symbol": symbol,
        "timestamp": timestamp,
        "liquidity": str(liquidity),
        "delta_liquidity": str(delta_liquidity),
        "echo": str(echo),
        "mindshare": str(mindshare),
        "delta_mindshare": str(delta_mindshare),
        "holders": str(holders),
        "delta_holders": str(delta_holders),
    }
    collection.insert_one(data)
    print(f"[INFO] {symbol} - Saved to MongoDB: {data}")

def get_last_timestamp(symbol):
    """Finds the most recent timestamp for a given symbol"""
    latest_entry = collection.find_one({"symbol": symbol}, sort=[("timestamp", -1)])
    return datetime.strptime(latest_entry["timestamp"], '%Y-%m-%d %H:%M') if latest_entry else None

def backfill_historical_data(symbol):
    """Fills missing historical data for a single symbol before real-time fetching"""
    last_timestamp = get_last_timestamp(symbol)

    if last_timestamp:
        print(f"[INFO] {symbol} - Last recorded timestamp: {last_timestamp}")
        start_date = last_timestamp + timedelta(minutes=1)
    else:
        print(f"[INFO] {symbol} - No records found. Backfilling last 31 days...")
        start_date = datetime.utcnow() - timedelta(days=31)

    while start_date <= datetime.utcnow():
        timestamp = start_date.strftime('%Y-%m-%d %H:%M')
        fetch_and_store_data(timestamp, symbol)
        start_date += timedelta(minutes=1)  # Move to next minute

    print(f"[INFO] {symbol} - Backfill completed. Now starting real-time fetching...")

def fetch_real_time(symbol):
    """Fetches real-time data for a given symbol in an infinite loop"""
    backfill_historical_data(symbol)  # Ensure historical data is available
    while True:
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
        fetch_and_store_data(timestamp, symbol)
        time.sleep(60)  # Fetch every minute

def start_threads():
    """Creates and starts a separate thread for each coin"""
    threads = []
    for token in TOKENS:
        symbol = token.replace("USDT", "")
        thread = threading.Thread(target=fetch_real_time, args=(symbol,))
        thread.start()
        threads.append(thread)
        time.sleep(1)  # Small delay to prevent API rate limits

    # Keep main thread alive
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    delete_old_data()  # Clean up old records before starting
    start_threads()  # Start multi-threaded data fetching