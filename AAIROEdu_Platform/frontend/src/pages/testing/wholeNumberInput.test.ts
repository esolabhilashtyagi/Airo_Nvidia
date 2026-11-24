import { describe, expect, it } from 'vitest';
import { isWholeNumberInRange, normalizeWholeNumberInput } from './wholeNumberInput';

describe('whole number assessment inputs', () => {
  it('keeps an erased field blank and removes leading zeroes', () => {
    expect(normalizeWholeNumberInput('')).toBe('');
    expect(normalizeWholeNumberInput('05')).toBe('5');
  });

  it('rejects decimal and non-digit edits instead of coercing them', () => {
    expect(normalizeWholeNumberInput('5.5')).toBeNull();
    expect(normalizeWholeNumberInput('5a')).toBeNull();
  });

  it('requires a whole number inside the configured limits', () => {
    expect(isWholeNumberInRange('', 1, 50)).toBe(false);
    expect(isWholeNumberInRange('5', 1, 50)).toBe(true);
    expect(isWholeNumberInRange('51', 1, 50)).toBe(false);
    expect(isWholeNumberInRange('2.5', 1, 50)).toBe(false);
  });
});
