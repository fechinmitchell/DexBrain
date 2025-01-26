import React, { useState, useEffect } from "react";
import "./App.css";
import HypeMeter from "./HypeMeter";

/** A collection of interesting crypto facts */
const CRYPTO_FACTS = [
  "Bitcoin's pseudonymous creator, Satoshi Nakamoto, has never been identified.",
  "Ethereum introduced smart contracts in 2015, revolutionizing decentralized applications.",
  "The first real-world Bitcoin transaction was for two pizzas, costing 10,000 BTC in 2010.",
  "The total supply of Bitcoin is capped at 21 million coins.",
  "Binance is the largest cryptocurrency exchange by trading volume globally.",
  "Dogecoin started as a meme but became popular due to its active community and support from Elon Musk.",
  "Tether (USDT) is the most widely used stablecoin in the crypto ecosystem.",
  "The term 'HODL' originated from a misspelled word in a Bitcoin forum post in 2013.",
  "DeFi, or decentralized finance, allows financial transactions without intermediaries.",
  "NFTs, or non-fungible tokens, gained massive popularity in 2021 as digital collectibles.",
  "The Ethereum network will transition to Ethereum 2.0, introducing proof of stake (PoS).",
  "Bitcoin mining consumes more energy than some entire countries.",
  "Ripple (XRP) is designed to facilitate fast and low-cost cross-border payments.",
  "Satoshi Nakamoto's Bitcoin address contains about 1 million BTC, untouched since its creation.",
  "Litecoin was created in 2011 as a 'lighter' alternative to Bitcoin.",
  "Smart contracts are self-executing contracts with the terms of the agreement directly written in code.",
  "Polkadot enables interoperability between multiple blockchains.",
  "The CryptoPunks NFT collection was one of the first major NFT projects on Ethereum.",
  "Cardano uses a proof-of-stake consensus mechanism called Ouroboros.",
  "Blockchain technology ensures data is immutable and decentralized.",
  "Bitcoin halvings occur approximately every four years, reducing mining rewards by half.",
  "The first altcoin created was Namecoin in 2011.",
  "The Lightning Network enables faster and cheaper Bitcoin transactions.",
  "Proof of work (PoW) was the original consensus mechanism for blockchain networks.",
  "Staking allows crypto holders to earn rewards by locking up their tokens.",
  "Decentralized exchanges (DEXs) operate without a central authority.",
  "Solana is known for its high transaction speed and low fees.",
  "Chainlink enables smart contracts to access off-chain data securely.",
  "The most expensive NFT ever sold was Beeple's 'Everydays: The First 5000 Days' for $69.3 million.",
  "Crypto wallets can be categorized into hot wallets (online) and cold wallets (offline).",
  "Monero is a privacy-focused cryptocurrency that obscures transaction details.",
  "A DAO (Decentralized Autonomous Organization) is managed by community members via smart contracts.",
  "Bitcoin's whitepaper was published on October 31, 2008.",
  "The first Bitcoin block, called the Genesis Block, was mined in January 2009.",
  "Stablecoins are pegged to traditional currencies like USD to reduce volatility.",
  "Cryptography ensures the security and integrity of blockchain networks.",
  "The total market capitalization of cryptocurrencies surpassed $3 trillion in 2021.",
  "EOS was designed for scalability and to support industrial-scale dApps.",
  "Tezos is a self-upgrading blockchain with a focus on on-chain governance.",
  "A private key is required to access and manage cryptocurrency funds.",
  "Zcash provides enhanced privacy by using zero-knowledge proofs.",
  "Uniswap is one of the most popular decentralized exchanges using automated market makers.",
  "Mining pools allow multiple miners to combine resources and share rewards.",
  "Avalanche supports multiple custom blockchains on its platform.",
  "Terra's ecosystem focuses on stablecoins for decentralized finance applications.",
  "Metamask is a popular Ethereum wallet and browser extension for dApp access.",
  "The Bitcoin network processes approximately 7 transactions per second.",
  "Vitalik Buterin is the co-founder of Ethereum and a prominent figure in the crypto world.",
  "Security tokens represent real-world assets like stocks or real estate on the blockchain.",
  "Crypto adoption is growing rapidly, with countries like El Salvador embracing Bitcoin as legal tender."
];

function App() {
  // All categories in state
  const [allData, setAllData] = useState({
    trending: [],
    newly_launched: [],
    top_gainers: [],
    top_losers: []
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [category, setCategory] = useState("trending");
  const [factIndex, setFactIndex] = useState(0);

  // Use either your Render URL or local dev
  const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:5003";

  useEffect(() => {
    const MIN_LOADING_TIME = 3000;
    const startTime = Date.now();

    const fetchAllData = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/all`);
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        const data = await res.json();
        setAllData({
          trending: data.trending || [],
          newly_launched: data.newly_launched || [],
          top_gainers: data.top_gainers || [],
          top_losers: data.top_losers || []
        });

        const elapsedTime = Date.now() - startTime;
        const remainingTime = MIN_LOADING_TIME - elapsedTime;
        if (remainingTime > 0) {
          setTimeout(() => setLoading(false), remainingTime);
        } else {
          setLoading(false);
        }
      } catch (err) {
        setError(err.toString());
        setLoading(false);
      }
    };

    fetchAllData();

    // Random crypto facts
    const getNewFactIndex = (currentIndex) => {
      if (CRYPTO_FACTS.length <= 1) return 0;
      let newIdx = currentIndex;
      while (newIdx === currentIndex) {
        newIdx = Math.floor(Math.random() * CRYPTO_FACTS.length);
      }
      return newIdx;
    };

    setFactIndex(Math.floor(Math.random() * CRYPTO_FACTS.length));

    // Rotate facts every 5 seconds while loading
    let intervalId;
    if (loading) {
      intervalId = setInterval(() => {
        setFactIndex((prevIndex) => getNewFactIndex(prevIndex));
      }, 5000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [API_BASE_URL, loading]);

  const handleCategoryClick = (cat) => setCategory(cat);

  // tokens from chosen category
  const tokens = allData[category] || [];

  // sort by sentiment_score (unknown goes last)
  const sortedTokens = tokens.slice().sort((a, b) => {
    const aScore = a.sentiment_score;
    const bScore = b.sentiment_score;
    if (aScore === "unknown" && bScore === "unknown") return 0;
    if (aScore === "unknown") return 1;
    if (bScore === "unknown") return -1;
    return bScore - aScore; // descending
  });

  if (loading) {
    const fact = CRYPTO_FACTS[factIndex];
    return (
      <div className="futuristic-loading-screen">
        <div className="spinner"></div>
        <h2>Loading DexBrain Data...</h2>
        <p className="crypto-fact">{fact}</p>
      </div>
    );
  }

  if (error) {
    const fact = CRYPTO_FACTS[factIndex];
    return (
      <div className="futuristic-loading-screen">
        <div className="spinner"></div>
        <h2>Loading DexBrain Data...</h2>
        <p className="crypto-fact">{fact}</p>
      </div>
    );
  }

  return (
    <div className="App">
      <h1>DexBrain - Token Scanner (No Twitter Analysis)</h1>
      <p className="intro-text">Scan trending, newly launched, top gainers, and top losers.</p>

      <div className="category-buttons">
        <button 
          className={`glow-button ${category === "trending" ? "active" : ""}`}
          onClick={() => handleCategoryClick("trending")}
        >
          Trending
        </button>
        <button 
          className={`glow-button ${category === "newly_launched" ? "active" : ""}`}
          onClick={() => handleCategoryClick("newly_launched")}
        >
          Newly Launched
        </button>
        <button 
          className={`glow-button ${category === "top_gainers" ? "active" : ""}`}
          onClick={() => handleCategoryClick("top_gainers")}
        >
          Top Gainers
        </button>
        <button 
          className={`glow-button ${category === "top_losers" ? "active" : ""}`}
          onClick={() => handleCategoryClick("top_losers")}
        >
          Top Losers
        </button>
      </div>

      <div className="token-container">
        {sortedTokens.map((token, idx) => (
          <div key={idx} className="token-card">
            <h2>{token.name} ({token.symbol?.toUpperCase()})</h2>
            <p>Market Cap Rank: {token.market_cap_rank}</p>
            <p>Market Cap: {token.market_cap !== "N/A" ? `$${Number(token.market_cap).toLocaleString()}` : "N/A"}</p>
            <p>Price (USD): {token.price_usd !== "N/A" ? `$${Number(token.price_usd).toLocaleString()}` : "N/A"}</p>
            <p><strong>AI Analysis:</strong> {token.gpt_analysis}</p>

            <div className="sentiment-container">
              <h4 className="sentiment-label">Reddit Hype Meter</h4>
              <HypeMeter score={token.reddit_sentiment} />
              {token.sentiment_score === "unknown" && (
                <p className="sentiment-unknown">No Combined Sentiment (Twitter Disabled)</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;