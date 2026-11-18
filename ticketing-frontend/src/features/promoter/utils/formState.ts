export function hasUnsavedChanges<T extends object>(
  current: T,
  initial: T,
  hasPendingFile = false
): boolean {
  if (hasPendingFile) return true;

  return Object.keys(initial).some((key) => {
    const field = key as keyof T;
    return current[field] !== initial[field];
  });
}
