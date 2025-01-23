import React, { useState, useEffect } from "react";
import "./App.css";  
import HypeMeter from "./HypeMeter";

function App() {
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("http://localhost:5003/api/trending-tokens")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setTokens(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.toString());
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="loading"><h2>Loading tokens...</h2></div>;
  }

  if (error) {
    return <div className="error"><h2>Error: {error}</h2></div>;
  }

  if (!Array.isArray(tokens)) {
    return (
      <div className="unexpected-data">
        <h2>Unexpected Data</h2>
        <pre>{JSON.stringify(tokens, null, 2)}</pre>
      </div>
    );
  }

  return (
    <div className="App">
      <h1>DexBrain - Trending Token Scanner</h1>
      <div className="token-container">
        {tokens.map((token, index) => (
          <div key={index} className="token-card">
            <h2>{token.name} ({token.symbol})</h2>
            <p>Market Cap Rank: {token.market_cap_rank}</p>
            <p>Market Cap: ${token.market_cap.toLocaleString()}</p> {/* Display Market Cap */}
            <p>Price (USD): ${token.price_usd.toLocaleString()}</p>
            <p><strong>AI Analysis:</strong> {token.gpt_analysis}</p>
            {(token.sentiment_score !== undefined || token.twitter_sentiment === "unknown") && (
              <div className="sentiment-container">
                <h4 className="sentiment-label">Reddit Hype Meter</h4>
                <HypeMeter score={token.sentiment_score} />
                {token.twitter_sentiment === "unknown" && (
                  <p className="sentiment-unknown">Twitter Sentiment: Unknown</p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
