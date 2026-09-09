import base64
from html import escape

PALETTE = ["#8B0000", "#1B4332", "#1E3A8A", "#4A044E", "#713F12", "#374151", "#7C2D12", "#134E4A"]


def initials_avatar(name, bg_color="#3a3a3a"):
    initials = escape("".join(part[0] for part in (name or "").split(" ") if part)[:2].upper())
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
      <rect width="200" height="200" fill="{escape(bg_color, quote=True)}" />
      <text x="100" y="100" font-family="IBM Plex Sans, Arial, sans-serif" font-size="80"
            font-weight="bold" fill="#ffffff" text-anchor="middle" dominant-baseline="central">
        {initials}
      </text>
    </svg>'''
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def color_for_id(person_id):
    value = 0
    for char in str(person_id):
        value = (value * 31 + ord(char)) % len(PALETTE)
    return PALETTE[value]
