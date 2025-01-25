"""
DexBrain - A futuristic trending token scanner with sentiment-based hype meter
using real CoinGecko endpoints for multiple categories:
 - Trending
 - Newly Launched (approx)
 - Top Gainers
 - Top Losers

All categories are returned together at /api/all, so the frontend shows a single
loading screen until all data is loaded.
"""

from flask import Flask, jsonify
from flask_cors import CORS
import requests
import logging
import openai
import os
import time

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Sentiment and social media imports
import praw
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import tweepy

###############################################################################
# Configuration & Setup
###############################################################################

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DexBrain")

# Environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY", "")
reddit = praw.Reddit(
    client_id=os.environ.get("REDDIT_CLIENT_ID"),
    client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
    user_agent=os.environ.get("REDDIT_USER_AGENT", "DexBrainSentiment/0.1 by Important-Tooth4506")
)
sentiment_analyzer = SentimentIntensityAnalyzer()
twitter_client = tweepy.Client(bearer_token=os.environ.get("TWITTER_BEARER_TOKEN", ""))

# CoinGecko base URL
COINGECKO_API = "https://api.coingecko.com/api/v3"
FETCH_INTERVAL = 24 * 60 * 60  # once a day

CATEGORIES = ["trending", "newly_launched", "top_gainers", "top_losers"]
DATA_CACHE = {cat: [] for cat in CATEGORIES}
LAST_FETCH_TIMESTAMP = {cat: 0 for cat in CATEGORIES}

###############################################################################
# GPT & Sentiment Helpers
###############################################################################

def analyze_with_gpt(token_info):
    """Perform GPT analysis (about ~70 words) referencing only USD-based metrics."""
    prompt = f"""
    Provide a concise (~70 words) analysis of the following crypto token data (in USD, no BTC references):

    {token_info}

    Consider market cap, sentiment scores, potential project growth.
    Return only text without any JSON or additional formatting.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a knowledgeable crypto analyst."},
                {"role": "user", "content": prompt.strip()}
            ],
            temperature=0.7,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Error during GPT analysis:", exc_info=e)
        return "Analysis not available."

def fetch_reddit_sentiment(query, limit=10):
    """Fetch Reddit posts for 'query' and average their VADER compound sentiment."""
    try:
        posts = reddit.subreddit("all").search(query, sort="new", limit=limit)
        scores = []
        for post in posts:
            content = f"{post.title} {post.selftext}"
            val = sentiment_analyzer.polarity_scores(content)["compound"]
            scores.append(val)
        return sum(scores)/len(scores) if scores else 0.0
    except Exception as e:
        logger.error("Error fetching Reddit sentiment:", exc_info=e)
        return "unknown"

def fetch_twitter_sentiment(query, limit=10):
    """Fetch tweets for 'query' and average compound sentiment."""
    try:
        tw = twitter_client.search_recent_tweets(query=query, max_results=limit, tweet_fields=["text"])
        scores = []
        if tw.data:
            for t in tw.data:
                score = sentiment_analyzer.polarity_scores(t.text)["compound"]
                scores.append(score)
        if scores:
            return sum(scores)/len(scores)
        return 0.0
    except tweepy.errors.TooManyRequests:
        logger.error("Hit Twitter rate limit.")
        return "unknown"
    except Exception as e:
        logger.error("Error fetching Twitter sentiment:", exc_info=e)
        return "unknown"

###############################################################################
# Category Fetchers
###############################################################################

def fetch_trending_coins():
    """Fetch trending coins from CoinGecko /search/trending."""
    logger.info("Fetching 'trending' from CoinGecko")
    try:
        url = f"{COINGECKO_API}/search/trending"
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        coins = []
        for c in data.get("coins", []):
            item = c.get("item", {})
            coins.append({
                "id": item.get("id"),
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "market_cap_rank": item.get("market_cap_rank")
            })
        return coins
    except Exception as e:
        logger.error("Error fetching trending coins:", exc_info=e)
        return []

def fetch_newly_launched_coins():
    """
    Approximate newly launched by fetching 50 smallest market-cap coins.
    (No official 'newly launched' endpoint.)
    """
    logger.info("Fetching 'newly_launched' approximation via market_cap_asc")
    try:
        url = f"{COINGECKO_API}/coins/markets?vs_currency=usd&order=market_cap_asc&per_page=50&page=1"
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        coins = []
        for coin in data:
            coins.append({
                "id": coin.get("id"),
                "symbol": coin.get("symbol"),
                "name": coin.get("name"),
                "market_cap_rank": coin.get("market_cap_rank")
            })
        return coins
    except Exception as e:
        logger.error("Error fetching newly launched coins:", exc_info=e)
        return []

def fetch_top_gainers_and_losers():
    """
    Fetch top 250 by market cap, sort by 24h price change, 
    take top 20 gainers and top 20 losers.
    """
    logger.info("Fetching /coins/markets?order=market_cap_desc for top_gainers/top_losers")
    try:
        url = f"{COINGECKO_API}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1&price_change_percentage=24h"
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        # sort descending by price_change_percentage_24h_in_currency
        sorted_by_change = sorted(data, key=lambda x: x.get("price_change_percentage_24h_in_currency", 0), reverse=True)
        top_gainers_data = sorted_by_change[:20]
        top_losers_data = sorted_by_change[-20:]

        top_gainers = []
        for coin in top_gainers_data:
            top_gainers.append({
                "id": coin.get("id"),
                "symbol": coin.get("symbol"),
                "name": coin.get("name"),
                "market_cap_rank": coin.get("market_cap_rank")
            })

        top_losers = []
        # reverse again so that the worst losers are last
        for coin in reversed(top_losers_data):
            top_losers.append({
                "id": coin.get("id"),
                "symbol": coin.get("symbol"),
                "name": coin.get("name"),
                "market_cap_rank": coin.get("market_cap_rank")
            })

        return top_gainers, top_losers
    except Exception as e:
        logger.error("Error fetching top gainers/losers:", exc_info=e)
        return ([], [])

###############################################################################
# Enhance + Cache
###############################################################################

def enhance_tokens(raw_tokens):
    """Add price, GPT analysis, and sentiments (Reddit/Twitter) to raw token data."""
    if not raw_tokens:
        return []
    ids = [t["id"] for t in raw_tokens if t.get("id")]
    price_map = {}
    cap_map = {}

    if ids:
        try:
            joined = ",".join(ids)
            url = f"{COINGECKO_API}/coins/markets?vs_currency=usd&ids={joined}"
            resp = requests.get(url)
            resp.raise_for_status()
            market_data = resp.json()
            for coin in market_data:
                cid = coin["id"]
                price_map[cid] = coin.get("current_price", "N/A")
                cap_map[cid] = coin.get("market_cap", "N/A")
        except Exception as e:
            logger.error("Error fetching coin market data:", exc_info=e)

    enriched = []
    for t in raw_tokens:
        cid = t.get("id", "unknown")
        name = t.get("name", "Unknown")
        symbol = t.get("symbol", "N/A")

        info = {
            "id": cid,
            "name": name,
            "symbol": symbol,
            "market_cap_rank": t.get("market_cap_rank", "N/A"),
            "price_usd": price_map.get(cid, "N/A"),
            "market_cap": cap_map.get(cid, "N/A")
        }

        # GPT
        gpt_text = analyze_with_gpt(info)

        # Sentiments
        red_s = fetch_reddit_sentiment(f"{name} {symbol}")
        tw_s = fetch_twitter_sentiment(name)
        if red_s == "unknown" and tw_s == "unknown":
            combined = "unknown"
        elif red_s == "unknown":
            combined = tw_s
        elif tw_s == "unknown":
            combined = red_s
        else:
            combined = (red_s + tw_s)/2

        info["gpt_analysis"] = gpt_text
        info["reddit_sentiment"] = red_s
        info["twitter_sentiment"] = tw_s
        info["sentiment_score"] = combined

        enriched.append(info)
    return enriched

def prefetch_all_categories():
    """Once-a-day fetch for trending, newly_launched, top_gainers, and top_losers."""
    now = time.time()

    # trending
    if now - LAST_FETCH_TIMESTAMP["trending"] >= FETCH_INTERVAL or not DATA_CACHE["trending"]:
        trending_raw = fetch_trending_coins()
        DATA_CACHE["trending"] = enhance_tokens(trending_raw)
        LAST_FETCH_TIMESTAMP["trending"] = now

    # newly_launched
    if now - LAST_FETCH_TIMESTAMP["newly_launched"] >= FETCH_INTERVAL or not DATA_CACHE["newly_launched"]:
        new_raw = fetch_newly_launched_coins()
        DATA_CACHE["newly_launched"] = enhance_tokens(new_raw)
        LAST_FETCH_TIMESTAMP["newly_launched"] = now

    # top_gainers & top_losers
    need_gainers = (now - LAST_FETCH_TIMESTAMP["top_gainers"] >= FETCH_INTERVAL or not DATA_CACHE["top_gainers"])
    need_losers = (now - LAST_FETCH_TIMESTAMP["top_losers"] >= FETCH_INTERVAL or not DATA_CACHE["top_losers"])
    if need_gainers or need_losers:
        gainers_raw, losers_raw = fetch_top_gainers_and_losers()
        DATA_CACHE["top_gainers"] = enhance_tokens(gainers_raw)
        DATA_CACHE["top_losers"] = enhance_tokens(losers_raw)
        LAST_FETCH_TIMESTAMP["top_gainers"] = now
        LAST_FETCH_TIMESTAMP["top_losers"] = now

###############################################################################
# Routes
###############################################################################

@app.route("/api/all", methods=["GET"])
def get_all():
    """
    Single route that returns all categories at once, so the frontend can 
    show a single loading screen until everything is ready.
    """
    prefetch_all_categories()
    return jsonify({
        "trending": DATA_CACHE["trending"],
        "newly_launched": DATA_CACHE["newly_launched"],
        "top_gainers": DATA_CACHE["top_gainers"],
        "top_losers": DATA_CACHE["top_losers"]
    })

@app.route("/")
def index():
    return "DexBrain - Multi-category real calls with once-a-day caching."

if __name__ == "__main__":
    logger.info("Starting DexBrain Flask app with multi-category real calls (single route).")
    prefetch_all_categories()  # optionally prefetch on startup
    app.run(host="0.0.0.0", port=5003, debug=False)
