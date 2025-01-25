// HypeMeter.js
import React from "react";
import "./App.css";

// If your sentiment is in range -1..+1, you can scale it to 0..1.
function HypeMeter({ score, label = "Hype" }) {
  if (score === "unknown") {
    return (
      <div className="hype-meter-container unknown">
        <p className="sentiment-unknown-label">{label} Unknown</p>
      </div>
    );
  }

  // If your sentiment is 0..1 already, no scaling needed
  // If your sentiment is -1..1, let's scale it
  const scaled = Math.max(0, Math.min(1, (score + 1) / 2));

  let description = "Moderate";
  if (scaled < 0.3) description = "Dead";
  else if (scaled > 0.7) description = "Huge";

  const totalSquares = 10;
  const filledCount = Math.round(scaled * totalSquares);
  const squares = [];
  for (let i = 0; i < totalSquares; i++) {
    squares.push(
      <div key={i} className={`hype-square ${i < filledCount ? "filled" : "empty"}`} />
    );
  }

  return (
    <div className="hype-meter-container">
      <div className="hype-meter-squares">{squares}</div>
      <div className="hype-meter-label">{label}: {description}</div>
    </div>
  );
}

export default HypeMeter;
