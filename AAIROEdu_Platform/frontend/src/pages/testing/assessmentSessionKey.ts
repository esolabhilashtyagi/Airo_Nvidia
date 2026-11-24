const SESSION_KEY = 'aairo_active_assessment_id';

export const assessmentSessionKey = (userId: string) => `${SESSION_KEY}:${userId}`;
