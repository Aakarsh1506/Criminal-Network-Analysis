// Hand-placed x/y percentages for positioning a city on the India.svg
// graphic. The DB stores lat/long, but the original UI was hand-illustrated
// against the SVG's own coordinate space, so this is an approximation, not
// a geographic projection. Adjust freely if a city looks off on the map.

export const CITY_COORDINATES = {
  Mumbai: { x: 22, y: 62 },
  "New Delhi": { x: 42, y: 24 },
  Bengaluru: { x: 36, y: 76 },
  Ahmedabad: { x: 18, y: 50 },
  Kolkata: { x: 71, y: 46 },
  Pune: { x: 25, y: 65 },
  Jaipur: { x: 33, y: 32 },
  Gurugram: { x: 41, y: 25 },
  Kochi: { x: 33, y: 88 },
  Hyderabad: { x: 42, y: 68 },
  Lucknow: { x: 48, y: 32 },
  Patna: { x: 58, y: 36 },
  Indore: { x: 33, y: 52 },
  Amritsar: { x: 33, y: 16 },
};

export function coordinatesForCity(city) {
  return CITY_COORDINATES[city] || { x: 50, y: 50 };
}