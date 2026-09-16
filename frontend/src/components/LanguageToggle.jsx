import { useEffect, useId, useState } from "react";
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

  useEffect(() => {
    if (typeof document !== "undefined") document.documentElement.lang = selected;
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
      <span className={`language-toggle-slider ${selected === "hi" ? "language-toggle-slider-hi" : "language-toggle-slider-en"}`} aria-hidden="true" />
      <button type="button" className="language-toggle-option" role="radio" aria-checked={selected === "hi"} aria-label="Switch to Hindi" disabled={disabled} tabIndex={selected === "hi" ? 0 : -1} onClick={() => selectLanguage("hi")}>H</button>
      <button type="button" className="language-toggle-option" role="radio" aria-checked={selected === "en"} aria-label="Switch to English" disabled={disabled} tabIndex={selected === "en" ? 0 : -1} onClick={() => selectLanguage("en")}>E</button>
    </div>
  );
}
