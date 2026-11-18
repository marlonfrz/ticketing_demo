export function getSafeRedirect(value: string | null, origin: string): string | null {
  if (!value) return null;

  try {
    const target = new URL(value, origin);
    if (target.origin !== origin || !target.pathname.startsWith("/")) return null;
    return `${target.pathname}${target.search}${target.hash}`;
  } catch {
    return null;
  }
}
