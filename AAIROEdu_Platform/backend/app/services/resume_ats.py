"""Deterministic, job-description-specific resume match estimate."""
from __future__ import annotations

import re
from collections import Counter


STOP_WORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "but", "by", "can", "candidate", "company",
    "design", "develop", "development", "do", "experience", "for", "from", "good", "have", "in", "include",
    "including", "into", "is", "it", "job", "looking", "must", "our", "or", "of", "on", "opportunity",
    "position", "preferred", "provide", "required", "requirement", "responsibility", "responsibilities", "role",
    "should", "team", "the", "their", "this", "to", "use", "using", "we", "well", "will", "with", "work",
    "you", "your", "years", "year", "skills", "skill", "ability", "strong", "knowledge", "understanding",
}

SECTION_PATTERNS = {
    "Summary": r"^(professional\s+)?(summary|profile|objective|about me)$",
    "Experience": r"^(professional\s+)?(work\s+)?(experience|employment|work history|professional history)$",
    "Education": r"^(education|academic background|qualifications)$",
    "Skills": r"^(technical\s+)?(skills|technologies|technical stack|competencies)$",
    "Projects": r"^(selected\s+)?(projects|selected work|portfolio)$",
}


def _keywords(job_description: str) -> list[str]:
    text = job_description.casefold()
    original_tokens = re.findall(r"(?<!\w)(?:[A-Za-z][A-Za-z0-9+#./-]{1,}|\.net|c\+\+|c#)(?!\w)", job_description)
    tokens = [token.casefold() for token in original_tokens]
    counts = Counter(token.strip("-./") for token in tokens)
    counts = Counter({word: count for word, count in counts.items() if len(word) > 1 and word not in STOP_WORDS})
    # Keep acronyms, product names, and repeated terms; single-use generic words do not overwhelm the match list.
    candidates = list(counts)
    return sorted(candidates, key=lambda word: (-counts[word], word))[:40]


def calculate_ats_match(resume_text: str, job_description: str) -> dict:
    """Calculate a repeatable keyword/section estimate; this is not a vendor ATS score."""
    resume = re.sub(r"\s+", " ", resume_text).casefold()
    keywords = _keywords(job_description)
    matched = [word for word in keywords if re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", resume)]
    missing = [word for word in keywords if word not in matched]
    keyword_score = round((len(matched) / len(keywords) * 100) if keywords else 0, 1)

    resume_lines = [re.sub(r"^[\W_]+|[\W_]+$", "", line).casefold().strip() for line in resume_text.splitlines() if line.strip()]
    matched_sections = [
        name for name, pattern in SECTION_PATTERNS.items()
        if any(len(line) <= 50 and re.fullmatch(pattern, line) for line in resume_lines)
    ]
    missing_sections = [name for name in SECTION_PATTERNS if name not in matched_sections]
    section_score = round(len(matched_sections) / len(SECTION_PATTERNS) * 100, 1)
    overall = round(keyword_score * 0.85 + section_score * 0.15, 1)

    warnings = []
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    normalized_lines = [re.sub(r"\s+", " ", line).casefold() for line in lines]
    duplicates = {line for line, count in Counter(normalized_lines).items() if count > 1 and len(line) > 20}
    if duplicates:
        warnings.append("Repeated text lines detected; check for duplicated content.")
    if any(len(line) > 240 for line in lines):
        warnings.append("Some text lines are unusually long; use concise bullets for easier parsing.")
    if len(lines) < 5:
        warnings.append("Extracted text is very short; verify parsing and resume content before relying on this estimate.")

    return {
        "ats_score": overall,
        "keyword_match_score": keyword_score,
        "section_match_score": section_score,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "matched_sections": matched_sections,
        "missing_sections": missing_sections,
        "formatting_warnings": warnings,
    }
