"""Shared helpers for the fleet module."""

# Approximate coordinates for Ethiopian cities used in routes / GPS demo data.
CITY_COORDS = {
    "Addis Ababa": (9.0054, 38.7636),
    "Adama": (8.5411, 39.2689),
    "Modjo": (8.5833, 39.1167),
    "Hawassa": (7.0469, 38.4953),
    "Shashemene": (7.2008, 38.5994),
    "Dire Dawa": (9.5931, 41.8661),
    "Bahir Dar": (11.5942, 37.3613),
    "Gondar": (12.6030, 37.4710),
    "Mekelle": (13.4967, 39.4753),
    "Dessie": (11.1262, 39.6363),
    "Jimma": (7.6734, 36.8344),
    "Arba Minch": (6.0203, 37.5641),
    "Moyale": (3.5256, 39.0564),
    "Gambella": (8.2500, 34.5833),
    "Assosa": (10.0622, 34.5333),
    "Djibouti": (11.8251, 42.5903),
    "Nekemte": (9.0800, 36.5464),
    "Ambo": (8.9833, 37.8500),
}


def coords_for(place: str):
    """Return (lat, lng) for a place name, tolerating partial matches."""
    if not place:
        return CITY_COORDS["Addis Ababa"]
    p = place.strip().lower()
    for name, coord in CITY_COORDS.items():
        if p == name.lower() or p in name.lower() or name.lower() in p:
            return coord
    return CITY_COORDS["Addis Ababa"]


def interpolate_points(origin, destination, n=24, jitter=0.03):
    """Interpolate n points between two (lat, lng) tuples with slight jitter."""
    import random

    lat1, lng1 = origin
    lat2, lng2 = destination
    pts = []
    for i in range(n):
        t = i / max(n - 1, 1)
        lat = lat1 + (lat2 - lat1) * t + random.uniform(-jitter, jitter)
        lng = lng1 + (lng2 - lng1) * t + random.uniform(-jitter, jitter)
        pts.append((round(lat, 5), round(lng, 5)))
    return pts
