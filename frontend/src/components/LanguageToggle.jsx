import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import "./LanguageToggle.css";

export default function LanguageToggle({ value, onChange, disabled = false, className = "" }) {
const isControlled = value === "hi" || value === "en";
const [internalValue, setInternalValue] = useState(() => {
if (typeof window === "undefined") return "en";
const saved = window.localStorage.getItem("language");
return saved === "hi" || saved === "en" ? saved : "en";
  });
const selected = isControlled ? value : internalValue;
const groupId = useId();

const hiRef = useRef(null);
const enRef = useRef(null);
const [sliderStyle, setSliderStyle] = useState({ width: 0, transform: "translateX(0px)" });

useEffect(() => {
if (typeof document !== "undefined") document.documentElement.lang = selected;
  }, [selected]);

useLayoutEffect(() => {
const activeEl = selected === "hi" ? hiRef.current : enRef.current;
const containerEl = activeEl?.parentElement;
if (!activeEl || !containerEl) return;

const update = () => {
const containerRect = containerEl.getBoundingClientRect();
const activeRect = activeEl.getBoundingClientRect();
setSliderStyle({
width: activeRect.width,
transform: `translateX(${activeRect.left - containerRect.left}px)`,
      });
    };

update();
// Re-measure on resize/font-load, since Devanagari and Latin text can
// shift width slightly after web fonts finish loading.
window.addEventListener("resize", update);
return () => window.removeEventListener("resize", update);
  }, [selected]);

function selectLanguage(next) {
if (disabled || next === selected) return;
if (!isControlled) setInternalValue(next);
if (typeof window !== "undefined") window.localStorage.setItem("language", next);
if (typeof document !== "undefined") document.documentElement.lang = next;
onChange?.(next);
  }

function handleKeyDown(event) {
if (disabled) return;
if (event.key === "ArrowLeft" || event.key === "Home") {
event.preventDefault();
selectLanguage("hi");
    } else if (event.key === "ArrowRight" || event.key === "End") {
event.preventDefault();
selectLanguage("en");
    }
  }

return (
<div id={groupId} className={`language-toggle ${disabled ? "language-toggle-disabled" : ""} ${className}`.trim()} role="radiogroup" aria-label="Select language" onKeyDown={handleKeyDown}>
      <span className="language-toggle-slider" aria-hidden="true" style={sliderStyle} />
      <button ref={hiRef} type="button" className="language-toggle-option" role="radio" aria-checked={selected === "hi"} aria-label="Switch to Hindi" disabled={disabled} tabIndex={selected === "hi" ? 0 : -1} onClick={() => selectLanguage("hi")}>हिंदी</button>
      <button ref={enRef} type="button" className="language-toggle-option" role="radio" aria-checked={selected === "en"} aria-label="Switch to English" disabled={disabled} tabIndex={selected === "en" ? 0 : -1} onClick={() => selectLanguage("en")}>English</button>
    </div>
  );
}