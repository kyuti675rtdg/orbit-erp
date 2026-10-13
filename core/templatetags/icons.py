"""Professional SVG icon set (stroke style, currentColor). Usage: {% icon 'truck' %} or {% icon name 20 %}."""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# 24x24 stroke icons (Lucide-style geometry, hand-authored)
ICONS = {
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.8-3.8"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.7 3.8 9S14.5 18.4 12 21c-2.5-2.6-3.8-5.7-3.8-9S9.5 5.6 12 3Z"/>',
    "layers": '<path d="m12 2.5 9.5 4.5L12 11.5 2.5 7 12 2.5Z"/><path d="m2.5 12 9.5 4.5L21.5 12"/><path d="m2.5 16.5 9.5 4.5 9.5-4.5"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V4H6.5A2.5 2.5 0 0 0 4 6.5v13Z"/><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>',
    "gift": '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M5 12v8a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-8M12 8v13M12 8s-4.5.3-5.5-2C5.7 4.3 7.5 3 9 3.8 10.5 4.6 12 8 12 8Zm0 0s4.5.3 5.5-2c.8-1.7-.7-3-2.2-2.2C13.8 4.6 12 8 12 8Z"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/>',
    "chat": '<path d="M21 12a8 8 0 0 1-8 8H4l2.3-2.9A8 8 0 1 1 21 12Z"/><path d="M8.5 11h7M8.5 14h4"/>',
    "briefcase": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 13h18"/>',
    "dashboard": '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    "tracking": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/>',
    "route": '<circle cx="6" cy="19" r="2.2"/><circle cx="18" cy="5" r="2.2"/><path d="M8.2 19H15a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h6.8"/>',
    "trips": '<circle cx="6" cy="19" r="2.2"/><circle cx="18" cy="5" r="2.2"/><path d="M8.2 19H15a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h6.8"/>',
    "clipboard": '<rect x="5" y="4" width="14" height="17" rx="2"/><rect x="9" y="2" width="6" height="4" rx="1"/><path d="M9 11h6M9 15h4"/>',
    "package": '<path d="M12 2.5 3.5 7v10L12 21.5 20.5 17V7L12 2.5Z"/><path d="M3.5 7 12 11.5 20.5 7M12 11.5V21.5"/>',
    "truck": '<path d="M1.5 6h12v10h-12z"/><path d="M13.5 10h4l3.5 3.5V16h-7.5"/><circle cx="6" cy="18.5" r="1.8"/><circle cx="17" cy="18.5" r="1.8"/>',
    "file": '<path d="M6 2.5h8L19 8v13.5H6z"/><path d="M13.5 2.5V8H19"/>',
    "map": '<path d="M9 4 3.5 6v14L9 18l6 2 5.5-2V4L15 6 9 4Z"/><path d="M9 4v14M15 6v14"/>',
    "pin": '<path d="M12 21.5s7-6.1 7-11.5A7 7 0 0 0 5 10c0 5.4 7 11.5 7 11.5Z"/><circle cx="12" cy="10" r="2.5"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4.5 20.5a7.5 7.5 0 0 1 15 0"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.8a3.5 3.5 0 0 1 0 6.4M17.5 14.2a6.5 6.5 0 0 1 4 5.8"/>',
    "idcard": '<rect x="2.5" y="5" width="19" height="14" rx="2"/><circle cx="8" cy="11" r="2"/><path d="M5.5 16a2.8 2.8 0 0 1 5 0M14 9.5h4.5M14 13h4.5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "card": '<rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="M2.5 10h19M6 15h4"/>',
    "fuel": '<path d="M5 21V6a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v15"/><path d="M4 21h12M15 9h2.5a2 2 0 0 1 2 2v6.5a1.5 1.5 0 0 0 3 0V9.5L20 7"/><path d="M8 7h6v4H8z"/>',
    "wrench": '<path d="M21 6.5a5 5 0 0 1-6.8 4.7L7 18.4a2.1 2.1 0 0 1-3-3l7.2-7.2A5 5 0 0 1 17.5 3l-2.6 2.6 2.5 2.5L21 6.5Z"/>',
    "shield": '<path d="M12 2.5 4.5 5.5v6c0 5 3.2 8.3 7.5 10 4.3-1.7 7.5-5 7.5-10v-6L12 2.5Z"/><path d="m9 11.5 2.2 2.2L15.5 9"/>',
    "gear": '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.8v3M12 18.2v3M2.8 12h3M18.2 12h3M5.5 5.5l2.1 2.1M16.4 16.4l2.1 2.1M18.5 5.5l-2.1 2.1M7.6 16.4l-2.1 2.1"/>',
    "warehouse": '<path d="M3 21V9.5L12 3l9 6.5V21"/><path d="M3 21h18M7.5 21v-6h9v6"/><path d="M7.5 17.5h9"/>',
    "box": '<path d="M12 2.5 3.5 7v10L12 21.5 20.5 17V7L12 2.5Z"/><path d="M3.5 7 12 11.5 20.5 7M12 11.5V21.5"/>',
    "receipt": '<path d="M5 2.5h14V22l-2.3-1.5L14.4 22l-2.4-1.5L9.6 22l-2.3-1.5L5 22V2.5Z"/><path d="M9 7.5h6M9 11.5h6"/>',
    "cash": '<rect x="2.5" y="6" width="19" height="12" rx="2"/><circle cx="12" cy="12" r="2.8"/><path d="M6 9.5h.01M18 14.5h.01"/>',
    "bank": '<path d="M3 9.5 12 4l9 5.5"/><path d="M4.5 9.5V18M9.8 9.5V18M14.2 9.5V18M19.5 9.5V18M3 21h18M3 18h18"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M8 16v-5M13 16V8M18 16v-8"/>',
    "bell": '<path d="M6 9a6 6 0 0 1 12 0c0 5 2 6.5 2 6.5H4S6 14 6 9Z"/><path d="M10 19.5a2.2 2.2 0 0 0 4 0"/>',
    "home": '<path d="M4 11 12 4l8 7"/><path d="M6 9.5V20h12V9.5"/>',
    "building": '<rect x="4.5" y="3" width="15" height="18" rx="1"/><path d="M9 7.5h2M13 7.5h2M9 11h2M13 11h2M9 14.5h2M13 14.5h2M10 21v-3h4v3"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.8-3.8"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "pencil": '<path d="M4 20h4L20 8l-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/>',
    "trash": '<path d="M4 7h16M9.5 7V4.5h5V7M6.5 7l1 13.5h9l1-13.5"/><path d="M10 11v6M14 11v6"/>',
    "back": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "check": '<path d="m4.5 12.5 5 5 10-11"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="16" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "alert": '<path d="M12 3.5 2.5 20h19L12 3.5Z"/><path d="M12 10v4M12 17.5h.01"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5h.01"/>',
    "timer": '<circle cx="12" cy="13" r="8"/><path d="M12 9.5V13l2.5 1.5M9.5 2.5h5"/>',
    "gauge": '<path d="M4 14a8 8 0 1 1 16 0"/><path d="M12 14l4-4"/><path d="M4 18h16"/>',
    "wallet": '<path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/><path d="M16 12.5h5v4h-5a2 2 0 0 1 0-4Z"/>',
    "logout": '<path d="M14 4H6v16h8"/><path d="m10 12 7-4v8l-7-4ZM17 8h4v8h-4"/>',
    "grid": '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "moon": '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
}


@register.simple_tag
def icon(name, size=18):
    """Render an SVG icon: {% icon 'truck' %} or {% icon name 20 %}."""
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = 18
    body = ICONS.get(str(name), ICONS["info"])
    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{body}</svg>'
    )
    return mark_safe(svg)
