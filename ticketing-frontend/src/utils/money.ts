export function formatMoney(value: number | string, currency: string): string {
  const amount = Number(value);

  if (!Number.isFinite(amount)) {
    return `${value} ${currency}`;
  }

  return `${amount.toFixed(2)} ${currency}`;
}
