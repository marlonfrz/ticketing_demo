export const SESSION_COOKIE = "session_token";

const backendApiUrl = (process.env.BACKEND_API_URL || "http://localhost:8000").replace(
  /\/$/,
  ""
);

export async function validateAccessToken(accessToken: string): Promise<boolean> {
  try {
    const response = await fetch(`${backendApiUrl}/auth/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  }
}

export function getAccessTokenExpiration(accessToken: string): Date | null {
  try {
    const payload = accessToken.split(".")[1];
    if (!payload) return null;

    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = JSON.parse(atob(normalized)) as { exp?: unknown };
    if (typeof decoded.exp !== "number") return null;

    const expiresAt = new Date(decoded.exp * 1000);
    return expiresAt.getTime() > Date.now() ? expiresAt : null;
  } catch {
    return null;
  }
}
