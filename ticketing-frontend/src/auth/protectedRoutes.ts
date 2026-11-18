const PROTECTED_PREFIXES = [
  "/profile",
  "/my-tickets",
  "/promoter",
  "/admin",
  "/validation-stations",
] as const;

const EVENT_MANAGE_PATTERN = /^\/events\/[^/]+\/manage$/;

export function isProtectedPath(pathname: string): boolean {
  return (
    PROTECTED_PREFIXES.some(
      (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
    ) || EVENT_MANAGE_PATTERN.test(pathname)
  );
}
