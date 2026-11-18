import "server-only";

const backendApiUrl = (process.env.BACKEND_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ServerApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ServerApiError";
  }
}

export async function serverApiRequest<T>(
  path: string,
  init: RequestInit & { next?: { revalidate?: number; tags?: string[] } } = {}
): Promise<T> {
  const response = await fetch(`${backendApiUrl}${path}`, init);

  if (!response.ok) {
    throw new ServerApiError(response.status, `API request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}
