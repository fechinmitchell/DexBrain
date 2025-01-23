"""
DexBrain - A futuristic trending token scanner with sentiment-based hype meter
Once-a-day aggregator combining:
- CoinGecko trending tokens
- GPT analysis
- Reddit sentiment
- Twitter sentiment
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
import tweepy  # Twitter API library

###############################################################################
# Configuration
###############################################################################

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains on all routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DexBrain")

# Set your OpenAI API key from environment variable
openai.api_key = os.environ.get("OPENAI_API_KEY", "YOUR_FALLBACK_OPENAI_KEY")

# Configure Reddit App Credentials using environment variables
reddit = praw.Reddit(
    client_id=os.environ.get("REDDIT_CLIENT_ID"),
    client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
    user_agent=os.environ.get("REDDIT_USER_AGENT", "DexBrainSentiment/0.1 by Important-Tooth4506")
)

# Initialize VADER sentiment analyzer
sentiment_analyzer = SentimentIntensityAnalyzer()

# Configure Twitter client using Tweepy with Bearer Token from .env
twitter_client = tweepy.Client(
    bearer_token=os.environ.get("TWITTER_BEARER_TOKEN")
)

COINGECKO_API = "https://api.coingecko.com/api/v3"
DATA_CACHE = []
LAST_FETCH_TIMESTAMP = 0
FETCH_INTERVAL = 24 * 60 * 60  # 24 hours

###############################################################################
# Utility Functions
###############################################################################

def fetch_trending_tokens():
    """Fetch trending tokens from CoinGecko."""
    try:
        url = f"{COINGECKO_API}/search/trending"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error("Error fetching data from CoinGecko:", exc_info=e)
        return {}

def analyze_with_gpt(token_info):
    """Perform GPT analysis on token_info, limited to ~70 words."""
    prompt = f"""
    Provide a concise (~70 words) analysis of the following crypto token data. Only refer to the price of the token or market cap in USD and not in BTC:
    {token_info}

    Consider factors like market cap, sentiment scores, and potential project growth.
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
            max_tokens=100  # Approximately 70 words
        )
        analysis = response.choices[0].message.content.strip()
        logger.info(f"GPT analysis successful for token: {token_info.get('name')}")
        return analysis
    except Exception as e:
        logger.error("Error during GPT analysis:", exc_info=e)
        return "Analysis not available."

def fetch_reddit_sentiment(query, limit=10):
    """Fetch recent Reddit posts for a query and return average sentiment score or 'unknown'."""
    try:
        posts = reddit.subreddit("all").search(query, sort="new", limit=limit)
        sentiments = []
        for post in posts:
            content = f"{post.title} {post.selftext}"
            score = sentiment_analyzer.polarity_scores(content)["compound"]
            sentiments.append(score)
        return (sum(sentiments) / len(sentiments)) if sentiments else 0.0
    except Exception as e:
        logger.error("Error fetching/analyzing Reddit sentiment:", exc_info=e)
        return "unknown"

def fetch_twitter_sentiment(query, max_results=10):
    """Fetch recent tweets for a query and return average sentiment score or 'unknown'."""
    try:
        tweets = twitter_client.search_recent_tweets(query=query, max_results=max_results, tweet_fields=['text'])
        sentiments = []
        if tweets.data:
            for tweet in tweets.data:
                text = tweet.text
                score = sentiment_analyzer.polarity_scores(text)["compound"]
                sentiments.append(score)
        return (sum(sentiments) / len(sentiments)) if sentiments else 0.0
    except tweepy.errors.TooManyRequests:
        logger.error("Hit Twitter rate limit.")
        return "unknown"
    except Exception as e:
        logger.error("Error fetching/analyzing Twitter sentiment:", exc_info=e)
        return "unknown"

def build_daily_results():
    """
    1. Fetch trending tokens from CoinGecko.
    2. Fetch their USD prices and market caps.
    3. For each token, get GPT analysis, Reddit & Twitter sentiment, and compute sentiment_score.
    4. Return a list of combined results.
    """
    data = fetch_trending_tokens()
    results = []

    if "coins" not in data:
        logger.error("Unexpected data structure from CoinGecko.")
        return [{"error": "Unexpected data structure from CoinGecko.", "raw": data}]

    # Gather info from trending tokens
    ids = []
    coins_info = []
    for entry in data["coins"]:
        item = entry.get("item", {})
        coin_id = item.get("id")
        if coin_id:
            ids.append(coin_id)
        coins_info.append({
            "id": coin_id,
            "name": item.get("name", "Unknown"),
            "symbol": item.get("symbol", "N/A"),
            "market_cap_rank": item.get("market_cap_rank", "N/A"),
            "price_btc": item.get("price_btc", 0),
            "score": item.get("score", 0),
        })

    # Fetch USD prices and market caps
    usd_prices = {}
    market_caps = {}
    if ids:
        try:
            ids_str = ",".join(ids)
            market_url = f"{COINGECKO_API}/coins/markets?vs_currency=usd&ids={ids_str}"
            market_response = requests.get(market_url)
            market_response.raise_for_status()
            market_data = market_response.json()
            for coin in market_data:
                usd_prices[coin["id"]] = coin.get("current_price", "N/A")
                market_caps[coin["id"]] = coin.get("market_cap", "N/A")
        except Exception as e:
            logger.error("Error fetching USD prices from CoinGecko:", exc_info=e)

    # Process analysis and sentiments for each coin
    for coin in coins_info:
        coin["price_usd"] = usd_prices.get(coin["id"], "N/A")
        coin["market_cap"] = market_caps.get(coin["id"], "N/A")

        # GPT analysis
        gpt_analysis = analyze_with_gpt(coin)

        # Reddit sentiment
        reddit_score = fetch_reddit_sentiment(coin["name"])

        # Twitter sentiment
        twitter_score = fetch_twitter_sentiment(coin["name"])

        # Handle unknown statuses for Reddit/Twitter
        reddit_unknown = reddit_score == "unknown"
        twitter_unknown = twitter_score == "unknown"

        if reddit_unknown and twitter_unknown:
            combined_sentiment = "unknown"
        elif reddit_unknown:
            combined_sentiment = twitter_score
        elif twitter_unknown:
            combined_sentiment = reddit_score
        else:
            combined_sentiment = (reddit_score + twitter_score) / 2

        # Assign values to coin
        coin["gpt_analysis"] = gpt_analysis
        coin["reddit_sentiment"] = reddit_score if not reddit_unknown else "unknown"
        coin["twitter_sentiment"] = twitter_score if not twitter_unknown else "unknown"
        coin["sentiment_score"] = combined_sentiment

        results.append(coin)

    return results

###############################################################################
# Flask Routes
###############################################################################

@app.route("/api/trending-tokens", methods=["GET"])
def get_trending_tokens():
    """
    Return data from our once-a-day cache. If 24 hours have passed, rebuild the data.
    """
    global DATA_CACHE, LAST_FETCH_TIMESTAMP

    now = time.time()
    if now - LAST_FETCH_TIMESTAMP >= FETCH_INTERVAL or not DATA_CACHE:
        logger.info("24 hours passed or cache empty. Fetching fresh data...")
        DATA_CACHE = build_daily_results()
        LAST_FETCH_TIMESTAMP = now
    else:
        logger.info("Using cached data.")

    return jsonify(DATA_CACHE)

@app.route("/")
def index():
    return "DexBrain Backend (Futuristic Edition) is running!"

if __name__ == "__main__":
    logger.info("Starting DexBrain Flask app in futuristic style...")
    # Initialize cache on startup
    DATA_CACHE = build_daily_results()
    LAST_FETCH_TIMESTAMP = time.time()
    app.run(host="0.0.0.0", port=5003, debug=False)
