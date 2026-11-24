/** Return a normalized whole-number input, null when the edit contains non-digits. */
export function normalizeWholeNumberInput(value: string): string | null {
  if (!/^\d*$/.test(value)) return null;
  return value.replace(/^0+(?=\d)/, '');
}

export function isWholeNumberInRange(value: string, minimum: number, maximum: number): boolean {
  if (!/^\d+$/.test(value)) return false;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= minimum && parsed <= maximum;
}
