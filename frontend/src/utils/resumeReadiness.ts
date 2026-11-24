import type { ResumeParsedData } from '../types';

export interface ReadinessCheck {
  label: string;
  score: number;
  maxScore: number;
  evidence: string;
}

export interface ResumeReadiness {
  score: number;
  checks: ReadinessCheck[];
  improvements: string[];
}

const SECTION_PATTERNS: Record<string, RegExp> = {
  Summary: /^(professional\s+)?(summary|profile|objective|about me)$/i,
  Experience: /^(professional\s+)?(work\s+)?(experience|employment|work history|professional history)$/i,
  Education: /^(education|academic background|qualifications)$/i,
  Skills: /^(technical\s+)?(skills|technologies|technical stack|competencies)$/i,
  Projects: /^(selected\s+)?(projects|selected work|portfolio)$/i,
};

const QUANTIFIED_OUTCOME = /(?<!\d)(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?:\+)?\s*(?:%|(?:x|k|m|ms|seconds?|minutes?|hours?|days?|users?|clients?|requests?|projects?|people)(?![a-z]))/i;

function countQuantifiedOutcomeLines(lines: string[]): number {
  let section: 'experience' | 'projects' | null = null;
  let count = 0;
  for (const line of lines) {
    const heading = line.replace(/^[\W_]+|[\W_]+$/g, '');
    if (/^(professional\s+)?(work\s+)?(experience|employment|work history|professional history)$/i.test(heading)) {
      section = 'experience';
      continue;
    }
    if (/^(selected\s+)?(projects|selected work|portfolio)$/i.test(heading)) {
      section = 'projects';
      continue;
    }
    if (/^(professional\s+)?(summary|profile|objective|about me|education|academic background|qualifications|skills|technical skills|technologies|technical stack|competencies)$/i.test(heading)) {
      section = null;
      continue;
    }
    if (section && QUANTIFIED_OUTCOME.test(line)) count += 1;
  }
  return count;
}

function clean(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

/**
 * A transparent, deterministic readiness heuristic over the candidate's extracted
 * resume. It is not a score from an employer's ATS and does not predict hiring.
 */
export function calculateResumeReadiness(rawText: string, parsed: ResumeParsedData): ResumeReadiness | null {
  const text = rawText.trim();
  if (!text) return null;

  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const contact = parsed.contact_info ?? {};
  const email = Object.entries(contact).some(([key, value]) => /email/i.test(key) && Boolean(clean(value)))
    || /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i.test(text);
  const phone = Object.entries(contact).some(([key, value]) => /phone|mobile|telephone/i.test(key) && Boolean(clean(value)))
    || /(?:\+?\d[\d ().-]{7,}\d)/.test(text);

  const sectionNames = Object.keys(SECTION_PATTERNS).filter((name) => {
    const hasHeading = lines.some((line) => SECTION_PATTERNS[name].test(line.replace(/^[\W_]+|[\W_]+$/g, '')));
    const data = parsed as unknown as Record<string, unknown>;
    const hasExtractedData = name === 'Summary' ? Boolean(clean(data.professional_summary) || clean(data.summary))
      : name === 'Experience' ? Array.isArray(parsed.experience) && parsed.experience.length > 0
        : name === 'Education' ? Array.isArray(parsed.education) && parsed.education.length > 0
          : name === 'Skills' ? Array.isArray(parsed.skills) && parsed.skills.length > 0
            : Array.isArray(parsed.projects) && parsed.projects.length > 0;
    return hasHeading || hasExtractedData;
  });
  const skillCount = Array.isArray(parsed.skills) ? parsed.skills.filter((skill) => clean(skill)).length : 0;
  const measurableLines = countQuantifiedOutcomeLines(lines);
  const wordCount = text.match(/[\p{L}\p{N}][\p{L}\p{N}+#./-]*/gu)?.length ?? 0;
  const duplicateLines = new Set(lines.map((line) => line.replace(/\s+/g, ' ').toLowerCase())).size < lines.length;
  const hasCorruption = text.includes('\uFFFD');
  const hasOverlongLine = lines.some((line) => line.length > 240);

  const checks: ReadinessCheck[] = [
    { label: 'Contact details', score: Number(email) * 8 + Number(phone) * 7, maxScore: 15, evidence: `${email ? 'Email found' : 'Email not detected'} · ${phone ? 'Phone found' : 'Phone not detected'}` },
    { label: 'Standard resume sections', score: sectionNames.length * 6, maxScore: 30, evidence: `${sectionNames.length}/5 detected${sectionNames.length ? `: ${sectionNames.join(', ')}` : ''}` },
    { label: 'Skills section content', score: skillCount >= 5 ? 15 : skillCount > 0 ? Math.round(skillCount / 5 * 15) : 0, maxScore: 15, evidence: `${skillCount} extracted skill${skillCount === 1 ? '' : 's'}` },
    { label: 'Measurable experience or project bullets', score: Math.min(measurableLines, 3) * 5, maxScore: 15, evidence: `${measurableLines} line${measurableLines === 1 ? '' : 's'} with numeric evidence detected` },
    { label: 'Text readability and extraction', score: (wordCount >= 200 ? 10 : wordCount >= 80 ? 7 : wordCount >= 30 ? 4 : 1) + (lines.length >= 5 ? 5 : 2) + (hasCorruption ? 0 : 5) + (duplicateLines || hasOverlongLine ? 0 : 5), maxScore: 25, evidence: `${wordCount} words · ${lines.length} non-empty lines${hasCorruption ? ' · replacement characters found' : ''}${duplicateLines ? ' · duplicate lines found' : ''}${hasOverlongLine ? ' · unusually long line found' : ''}` },
  ];

  const improvements: string[] = [];
  if (!email || !phone) improvements.push(`Make sure your resume text includes a reachable ${!email && !phone ? 'email address and phone number' : !email ? 'email address' : 'phone number'}.`);
  const missingSections = Object.keys(SECTION_PATTERNS).filter((name) => !sectionNames.includes(name));
  if (missingSections.length) improvements.push(`Add clear headings for relevant sections that are missing: ${missingSections.join(', ')}.`);
  if (skillCount < 5) improvements.push('List your relevant tools and skills in a clearly labeled skills section; include only skills you can support with experience.');
  if (measurableLines < 3) improvements.push('Where accurate, strengthen experience or project bullets with scope and outcomes (for example, users served, time saved, or percentage change). Do not invent metrics.');
  if (hasCorruption || duplicateLines || hasOverlongLine || wordCount < 80 || lines.length < 5) improvements.push('Check the extracted-text preview against the original file; use clear section breaks, remove duplicated text, and keep bullets readable.');

  return { score: checks.reduce((total, check) => total + check.score, 0), checks, improvements };
}
