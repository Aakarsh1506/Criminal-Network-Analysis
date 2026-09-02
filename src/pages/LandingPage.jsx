import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import alleyBg from "/images/alley-bg.jpg";
import "./LandingPage.css";

function LandingPage() {
  const navigate = useNavigate();
  const [breaking, setBreaking] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleBreak = () => {
    if (breaking) return;
    setBreaking(true);
    // tear (0 - 0.6s) + push-forward (starts 0.5s, runs 0.65s) => ends ~1.15s
    timerRef.current = setTimeout(() => {
      navigate("/login");
    }, 1150);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleBreak();
    }
  };

  const tapeText = "CRIME SCENE DO NOT CROSS ".repeat(20);

  return (
    <div
      className={`landing-page ${breaking ? "breaching" : ""}`}
      style={{ "--bg-image": `url(${alleyBg})` }}
    >
      {/* Crossed crime scene tape — click/tap to tear through */}
      <div
        className={`tape-hero ${breaking ? "breaking" : ""}`}
        role="button"
        tabIndex={0}
        aria-label="Tear the tape to breach the scene"
        onClick={handleBreak}
        onKeyDown={handleKeyDown}
      >
        <div className="crime-tape tape-1">
          <div className="tape-half tape-half-left">
            <span className="tape-text">{tapeText}</span>
          </div>
          <div className="tape-half tape-half-right">
            <span className="tape-text">{tapeText}</span>
          </div>
        </div>
        <div className="crime-tape tape-2">
          <div className="tape-half tape-half-left">
            <span className="tape-text">{tapeText}</span>
          </div>
          <div className="tape-half tape-half-right">
            <span className="tape-text">{tapeText}</span>
          </div>
        </div>
        <div className="snap-flash" aria-hidden="true" />
      </div>

      {/* Content below the tape crossing */}
      <div className="cover-content">
        <span className="cover-eyebrow">AI-Powered</span>
        <h1 className="cover-title">
          Criminal Network
          <br />
          Analysis System
        </h1>
        <p className="cover-subtitle">
          Uncover connections. Predict threats. Protect society.
        </p>

        <p className="tear-hint">Tap the tape to breach the scene</p>
      </div>

      {/* Forward push tunnel — sells the "walking into the scene" transition */}
      <div className="forward-tunnel" aria-hidden="true" />
    </div>
  );
}

export default LandingPage;