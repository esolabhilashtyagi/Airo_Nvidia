import { describe, expect, it } from 'vitest';
import { calculateResumeReadiness } from './resumeReadiness';
import type { ResumeParsedData } from '../types';

const emptyParsed = {
  contact_info: {}, skills: [], skill_categories: {}, education: [], experience: [], projects: [],
  certifications: [], publications: [], awards: [], languages: [],
} as ResumeParsedData;

describe('resume readiness estimate', () => {
  it('calculates a repeatable score from detected resume evidence without a job description', () => {
    const text = `Alex Candidate\nalex@example.com\n+1 415 555 1234\nProfessional Summary\nExperienced software engineer\nExperience\nImproved service latency by 35%\nEducation\nBSc Computer Science\nSkills\nPython TypeScript React SQL\nProjects\nBuilt a portfolio application`;
    const data = { ...emptyParsed, contact_info: {}, skills: ['Python', 'TypeScript', 'React', 'SQL', 'Docker'], experience: [{}], education: [{}], projects: ['portfolio'] };
    const first = calculateResumeReadiness(text, data);
    const second = calculateResumeReadiness(text, data);

    expect(first).not.toBeNull();
    expect(first?.score).toBeGreaterThan(0);
    expect(first?.score).toBeLessThanOrEqual(100);
    expect(second).toEqual(first);
    expect(first?.checks.find((check) => check.label === 'Contact details')?.score).toBe(15);
    expect(first?.improvements).toEqual(expect.arrayContaining([expect.stringContaining('Do not invent metrics') ]));
  });

  it('does not produce a score without extracted text', () => {
    expect(calculateResumeReadiness('  ', emptyParsed)).toBeNull();
  });

  it('reflects missing evidence in a sparse resume instead of returning a fixed score', () => {
    const sparse = calculateResumeReadiness('Developer\nBuilt an app', emptyParsed);
    expect(sparse?.score).toBeLessThan(50);
    expect(sparse?.improvements.length).toBeGreaterThan(0);
  });

  it('counts quantified outcomes under experience and projects, not phone numbers or dates', () => {
    const text = `Alex Candidate\n+1 415 555 1234\nExperience\nSoftware Engineer · 2021–2024\nReduced onboarding friction by60%through redesigned flows.\nProjects\nBuilt an application used by 5,000+ users\nEducation\nGraduated in 2022`;
    const result = calculateResumeReadiness(text, emptyParsed);
    const evidence = result?.checks.find((check) => check.label === 'Measurable experience or project bullets')?.evidence;
    expect(evidence).toBe('2 lines with numeric evidence detected');
  });
});
