const SAFE_STATION_SESSION_TOKEN = /^[A-Za-z0-9._~-]+$/;

export const VALIDATION_STATION_COOKIE = "validator_station_session";

export function getValidationStationCookieHeader(
  path: string[],
  token: string | undefined
): string | null {
  if (
    path[0] !== "validator-stations" ||
    !token ||
    !SAFE_STATION_SESSION_TOKEN.test(token)
  ) {
    return null;
  }

  return `${VALIDATION_STATION_COOKIE}=${token}`;
}
