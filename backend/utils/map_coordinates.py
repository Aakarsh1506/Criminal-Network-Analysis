# Positions on the frontend map, rather than geographic latitude and longitude.
CITY_COORDINATES = {
    "Mumbai": {"x": 22, "y": 62},
    "New Delhi": {"x": 42, "y": 24},
    "Bengaluru": {"x": 36, "y": 76},
    "Ahmedabad": {"x": 18, "y": 50},
    "Kolkata": {"x": 71, "y": 46},
    "Pune": {"x": 25, "y": 65},
    "Jaipur": {"x": 33, "y": 32},
    "Gurugram": {"x": 41, "y": 25},
    "Kochi": {"x": 33, "y": 88},
    "Hyderabad": {"x": 42, "y": 68},
    "Lucknow": {"x": 48, "y": 32},
    "Patna": {"x": 58, "y": 36},
    "Indore": {"x": 33, "y": 52},
    "Amritsar": {"x": 33, "y": 16},
}


def coordinates_for_city(city):
    # Unknown cities use the map center; copy to protect the shared lookup.
    return CITY_COORDINATES.get(city, {"x": 50, "y": 50}).copy()
