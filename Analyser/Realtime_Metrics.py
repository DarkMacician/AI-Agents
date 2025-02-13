import time
import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime

# MongoDB Connection
uri = "mongodb+srv://prompt:123@cluster0.admu7.mongodb.net"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['Other_Information']
collection = db['Metrics']

# API Keys (Replace with actual keys)
ETHERSCAN_KEY = "4HJ6YPTJJ4BPS5158AFBX3MY49DPB2ZJ53"
BSCSCAN_KEY = "2X7CXUBXYZ4GYEHG6QATI8G6SHSBN7977G"
LUNARCRUSH_KEY = "egisnd83jy9jda8j1zw61lh2tm73h6it7ll6c7n6"

# Binance API
BINANCE_API = "https://api4.binance.com/api/v3/ticker/24hr"

# Token Symbols
TOKENS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]

# Last recorded mindshare & holders for delta calculation
last_mindshare = {}
last_holders = {}

def get_binance_data(symbol):
    """Fetches trading data from Binance API"""
    params = {"symbol": symbol}
    response = requests.get(BINANCE_API, params=params).json()
    return {
        "symbol": symbol.replace("USDT", ""),
        "liquidity": float(response.get("quoteVolume", 0)),
        "delta_liquidity": float(response.get("priceChangePercent", 0)),
    }

def get_etherscan_holders():
    """Fetches ETH holders from Etherscan"""
    url = f"https://api.etherscan.io/api?module=stats&action=ethsupply&apikey={ETHERSCAN_KEY}"
    response = requests.get(url).json()
    return int(response.get("result", 0))

def get_bscscan_holders():
    """Fetches BNB holders from BscScan"""
    url = f"https://api.bscscan.com/api?module=stats&action=bnbholders&apikey={BSCSCAN_KEY}"
    response = requests.get(url).json()
    return int(response.get("result", 0))

def get_solana_holders():
    """Fetches SOL holders from Solana RPC"""
    url = "https://api.mainnet-beta.solana.com"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getVoteAccounts",
        "params": []
    }
    response = requests.post(url, json=payload).json()
    return len(response["result"]["current"])  # Number of validators

def get_mindshare(symbol):
    """Fetches Mindshare (Social Dominance) from LunarCrush"""
    url = f"https://api.lunarcrush.com/v2?data=assets&key={LUNARCRUSH_KEY}&symbol={symbol}"
    response = requests.get(url).json()
    return float(response["data"][0]["social_dominance"])

def fetch_and_store_data():
    """Fetches all metrics and saves them to MongoDB"""
    global last_mindshare, last_holders
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M')  # Format timestamp

    for token in TOKENS:
        binance_data = get_binance_data(token)
        symbol = binance_data["symbol"]

        # Get holders count
        if symbol == "ETH":
            holders = get_etherscan_holders()
        elif symbol == "BNB":
            holders = get_bscscan_holders()
        elif symbol == "SOL":
            holders = get_solana_holders()
        else:
            holders = 0  # BTC has no holders

        # Get mindshare & delta mindshare
        try:
            mindshare = get_mindshare(symbol)
            delta_mindshare = mindshare - last_mindshare.get(symbol, mindshare)
            last_mindshare[symbol] = mindshare
        except Exception:
            mindshare, delta_mindshare = 0, 0

        # Calculate delta holders
        delta_holders = holders - last_holders.get(symbol, holders)
        last_holders[symbol] = holders

        # Store data
        data = {
            "symbol": symbol,
            "timestamp": now,  # Formatted timestamp
            "liquidity": str(binance_data["liquidity"]),
            "delta_liquidity": str(binance_data["delta_liquidity"]),
            "mindshare": str(mindshare),
            "delta_mindshare": str(delta_mindshare),
            "holders": str(holders),  # Ensure it's within 64-bit range
            "delta_holders": str(delta_holders),
        }

        # Save to MongoDB
        collection.insert_one(data)
        print(f"Saved to MongoDB: {data}")

# Run script
fetch_and_store_data()