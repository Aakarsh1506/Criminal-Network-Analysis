// City centres from neo4j/import_data.cypher; bounds from India.svg.
const cities = {"Mumbai": [19.076, 72.8777], "New Delhi": [28.6139, 77.209], "Bengaluru": [12.9716, 77.5946], "Ahmedabad": [23.0225, 72.5714], "Kolkata": [22.5726, 88.3639], "Pune": [18.5204, 73.8567], "Jaipur": [26.9124, 75.7873], "Gurugram": [28.4595, 77.0266], "Kochi": [9.9312, 76.2673], "Hyderabad": [17.385, 78.4867], "Lucknow": [26.8467, 80.9462], "Patna": [25.5941, 85.1376], "Indore": [22.7196, 75.8577], "Amritsar": [31.634, 74.8723]};

const mercator = (latitude) => Math.log(Math.tan(Math.PI / 4 + latitude * Math.PI / 360));
export function mapPoint(city) {
  const coordinates = cities[city];
  if (!coordinates) return null;
  const [latitude, longitude] = coordinates;
  const north = mercator(37.084109);
  const south = mercator(6.753659);
  return {
    x: (longitude - 68.184010) / (97.418146 - 68.184010) * 611.85999,
    y: (north - mercator(latitude)) / (north - south) * 695.70178,
  };
}
