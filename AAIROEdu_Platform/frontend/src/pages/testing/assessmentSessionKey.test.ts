import { describe, expect, it } from 'vitest';
import { assessmentSessionKey } from './assessmentSessionKey';

describe('assessment browser session keys', () => {
  it('keeps resumable attempts isolated between candidate accounts', () => {
    expect(assessmentSessionKey('candidate-a')).not.toBe(assessmentSessionKey('candidate-b'));
    expect(assessmentSessionKey('candidate-a')).toBe('aairo_active_assessment_id:candidate-a');
  });
});
