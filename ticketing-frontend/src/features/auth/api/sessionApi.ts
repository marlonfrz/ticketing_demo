async function assertSuccessfulSessionResponse(response: Response): Promise<void> {
  if (!response.ok) {
    throw new Error(`Session request failed with ${response.status}`);
  }
}

export async function createServerSession(accessToken: string): Promise<void> {
  const response = await fetch("/auth/session", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    credentials: "same-origin",
  });
  await assertSuccessfulSessionResponse(response);
}

export async function clearServerSession(): Promise<void> {
  const response = await fetch("/auth/session", {
    method: "DELETE",
    credentials: "same-origin",
  });
  await assertSuccessfulSessionResponse(response);
}
