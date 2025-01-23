import React from "react";
import "./App.css"; // Ensure your CSS handles the new class for unknown sentiment

function HypeMeter({ score, totalSquares = 10 }) {
  if (score === "unknown") {
    return (
      <div className="hype-meter-container unknown">
        <p className="sentiment-unknown-label">Sentiment: Unknown</p>
      </div>
    );
  }

  // Ensure the score is a number
  const numericScore = typeof score === "number" ? score : 0;

  // Clamp the score between 0 and 1
  const clampedScore = Math.max(0, Math.min(1, numericScore));

  let label = "Moderate";
  if (clampedScore < 0.3) label = "Dead";
  else if (clampedScore > 0.7) label = "Huge";

  const filledSquares = Math.round(clampedScore * totalSquares);

  const squares = [];
  for (let i = 0; i < totalSquares; i++) {
    const isFilled = i < filledSquares;
    squares.push(
      <div
        key={i}
        className={`hype-square ${isFilled ? "filled" : "empty"}`}
      ></div>
    );
  }

  return (
    <div className="hype-meter-container">
      <div className="hype-meter-squares">{squares}</div>
      <div className="hype-meter-label">{label}</div>
    </div>
  );
}

export default HypeMeter;
