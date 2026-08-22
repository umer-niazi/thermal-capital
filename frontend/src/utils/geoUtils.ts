/**
 * Create a simple polygon approximating a circle around [lng, lat] with given radius in meters.
 */
export function createGeoJSONCircle(
  center: [number, number],
  radiusMeters: number = 14,
  points: number = 24
): [number, number][] {
  const coords: [number, number][] = [];
  const [lng, lat] = center;
  const distanceX = radiusMeters / (111320 * Math.cos((lat * Math.PI) / 180));
  const distanceY = radiusMeters / 110540;

  for (let i = 0; i <= points; i++) {
    const theta = (i / points) * (2 * Math.PI);
    const x = distanceX * Math.cos(theta);
    const y = distanceY * Math.sin(theta);
    coords.push([lng + x, lat + y]);
  }
  return coords;
}

/**
 * Generate a slight offset [lng, lat] around a center coordinate.
 */
export function generateOffsetCoordinate(
  center: [number, number],
  offsetIndex: number,
  totalItems: number = 6,
  radiusMeters: number = 20
): [number, number] {
  const [lng, lat] = center;
  const angle = ((offsetIndex % totalItems) / totalItems) * 2 * Math.PI + (offsetIndex * 0.4);
  const dist = radiusMeters * (0.6 + (offsetIndex % 3) * 0.3);
  const distanceX = dist / (111320 * Math.cos((lat * Math.PI) / 180));
  const distanceY = dist / 110540;

  return [lng + distanceX * Math.cos(angle), lat + distanceY * Math.sin(angle)];
}
