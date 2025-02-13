import time
import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta

# MongoDB Connection
uri = "mongodb+srv://prompt:123@cluster0.admu7.mongodb.net"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['MemeTradeCO']

# Dictionary mapping symbols to their collections
collections = {
    "BTCUSDT": db['BTCUSDT'],
    "ETHUSDT": db['ETHUSDT'],
    "SOLUSDT": db['SOLUSDT'],
    "BNBUSDT": db['BNBUSDT'],
    "ADAUSDT": db['ADAUSDT']
}

def fetch_historical_binance(symbol, start_time, end_time):
    url = "https://api.binance.com/api/v3/klines"
    interval = "1m"
    limit = 1000
    all_data = []

    while start_time < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
            "startTime": start_time,
            "endTime": end_time
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data:
            break

        all_data.extend(data)
        start_time = data[-1][0] + 1

    return all_data

def fetch_market_cap_binance(symbol):
    url = "https://api.binance.com/api/v3/ticker/24hr"
    params = {"symbol": symbol}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    return {
        "market_cap": float(data["quoteVolume"]) * float(data["lastPrice"]),
        "circulating_supply": float(data["quoteVolume"]) / float(data["lastPrice"])
    }

def save_to_mongodb(binance_data, symbol):
    market_cap_data = fetch_market_cap_binance(symbol)
    formatted_data = [
        {
            "timestamp": datetime.utcfromtimestamp(entry[0] / 1000).strftime('%Y-%m-%d %H:%M'),
            "open_price": float(entry[1]),
            "high_price": float(entry[2]),
            "low_price": float(entry[3]),
            "close_price": float(entry[4]),
            "volume": float(entry[5]),
            "market_cap": market_cap_data["market_cap"],
            "circulating_supply": market_cap_data["circulating_supply"],
            "symbol": symbol
        }
        for entry in binance_data
    ]
    collection = collections[symbol]
    if formatted_data:
        collection.insert_many(formatted_data)
        print(f"Saved {len(formatted_data)} records for {symbol} in MongoDB.")
    else:
        print(f"No data to save for {symbol}.")

def delete_old_records(symbol):
    collection = collections[symbol]
    threshold_date = datetime.utcnow() - timedelta(days=31)
    result = collection.delete_many({"timestamp": {"$lt": threshold_date.strftime('%Y-%m-%d %H:%M')}})
    print(f"Deleted {result.deleted_count} old records for {symbol}.")

def fetch_historical_data(symbol):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=31)
    print(f"Fetching historical data for {symbol}...")
    binance_data = fetch_historical_binance(symbol, int(start_time.timestamp() * 1000), int(end_time.timestamp() * 1000))
    save_to_mongodb(binance_data, symbol)

def fetch_real_time_data(symbols):
    while True:
        for symbol in symbols:
            collection = collections[symbol]
            last_entry = collection.find_one(sort=[("timestamp", -1)])

            if not last_entry:
                print(f"No records found for {symbol}, fetching last 30 days...")
                fetch_historical_data(symbol)

            new_data = fetch_historical_binance(symbol, int(datetime.utcnow().timestamp() * 1000), int(datetime.utcnow().timestamp() * 1000) + 60000)
            save_to_mongodb(new_data, symbol)
            delete_old_records(symbol)
            print(f"Inserted real-time data for {symbol}.")

        time.sleep(60)

if __name__ == "__main__":
    symbols = ["ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT", "BTCUSDT"]
    fetch_real_time_data(symbols)