// Generates a simple initials avatar as a self-contained SVG data URI —
// used whenever a person record has no stored photo (currently: everyone).

export function initialsAvatar(name, bgColor = "#3a3a3a") {
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
      <rect width="200" height="200" fill="${bgColor}" />
      <text x="100" y="100" font-family="IBM Plex Sans, Arial, sans-serif" font-size="80"
            font-weight="bold" fill="#ffffff" text-anchor="middle" dominant-baseline="central">
        ${initials}
      </text>
    </svg>
  `.trim();

  return `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`;
}

const PALETTE = ["#8B0000", "#1B4332", "#1E3A8A", "#4A044E", "#713F12", "#374151", "#7C2D12", "#134E4A"];

export function colorForId(id) {
  let hash = 0;
  for (const ch of String(id)) hash = (hash * 31 + ch.charCodeAt(0)) % PALETTE.length;
  return PALETTE[Math.abs(hash) % PALETTE.length];
}