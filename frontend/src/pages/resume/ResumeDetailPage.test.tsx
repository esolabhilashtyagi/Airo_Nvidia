// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { resumesApi } from '../../api/resumes';
import { ResumeDetailPage } from './ResumeDetailPage';

vi.mock('../../api/resumes', () => ({
  resumesApi: {
    getResume: vi.fn(),
    getAnalysis: vi.fn(),
    getATSReview: vi.fn(),
    extractJobDescription: vi.fn(),
    handleSuggestionAction: vi.fn(),
  },
}));

afterEach(() => cleanup());

describe('ResumeDetailPage', () => {
  it('removes job matching and does not request saved ATS match history', async () => {
    vi.mocked(resumesApi.getResume).mockResolvedValue({
      id: 'resume-1', file_name: 'candidate-resume.pdf', parsing_status: 'extracted',
      analysis_status: 'analysis_failed', extraction_confidence: 0.9,
      parsed_data: { skills: ['Python'] }, raw_text: 'Python engineer',
      versions: [], analysis_error: null, extraction_error: null,
    } as never);
    vi.mocked(resumesApi.getAnalysis).mockResolvedValue(null);
    vi.mocked(resumesApi.getATSReview).mockRejectedValue(new Error('ATS service unavailable (Reference: test-ref)'));

    render(
      <MemoryRouter initialEntries={['/resume/resume-1/analysis']}>
        <Routes><Route path="/resume/:resumeId/analysis" element={<ResumeDetailPage />} /></Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'candidate-resume.pdf' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Analyze resume' })).toBeTruthy();
    expect(screen.queryByText('Analysis unavailable')).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull();
    expect(resumesApi.getATSReview).not.toHaveBeenCalled();
    expect(screen.queryByText('Match this resume to a job')).toBeNull();
    expect(screen.queryByLabelText(/Upload job description/)).toBeNull();
    expect(resumesApi.getATSReview).not.toHaveBeenCalled();
  });

  it('shows the applied revised text draft after accepting a grounded suggestion', async () => {
    const baseResume = {
      id: 'resume-1', file_name: 'candidate-resume.pdf', parsing_status: 'extracted',
      analysis_status: 'analysis_completed', extraction_confidence: 0.9,
      parsed_data: { skills: ['Python'] }, raw_text: 'Experience\nBuilt reliable test suites\nEducation',
      versions: [], analysis_error: null, extraction_error: null,
    };
    const editedResume = {
      ...baseResume,
      parsed_data: { skills: ['Python'], enhanced_text: 'Experience\nBuilt reliable Python test suites\nEducation' },
      versions: [{ id: 'version-2', version_number: 2, created_at: '2026-11-20T00:00:00Z', content: {}, change_summary: 'Accepted Experience enhancement' }],
    };
    const suggestion = {
      id: 'suggestion-1', resume_analysis_id: 'analysis-1', category: 'Experience',
      original_text: 'Built reliable test suites', suggested_text: 'Built reliable Python test suites',
      reason: 'Retains the source claim and makes the existing skill explicit.',
      supporting_context: 'Built reliable test suites', status: 'pending' as const,
    };
    const analysis = { id: 'analysis-1', resume_id: 'resume-1', status: 'analysis_completed',
      overall_score: 81, category_scores: {}, completeness_score: 0, skills_relevance_score: 0,
      experience_quality_score: 0, target_role_alignment_score: 0, formatting_score: 0,
      strengths: [], weaknesses: [], missing_keywords: [], improvement_opportunities: [],
      extraction_confidence: 0.9, suggestions: [suggestion], created_at: '2026-11-20T00:00:00Z' };
    const acceptedAnalysis = { ...analysis, suggestions: [{ ...suggestion, status: 'accepted' as const }] };
    vi.mocked(resumesApi.getResume).mockResolvedValueOnce(baseResume as never).mockResolvedValueOnce(editedResume as never);
    vi.mocked(resumesApi.getAnalysis).mockResolvedValueOnce(analysis as never).mockResolvedValueOnce(acceptedAnalysis as never);
    vi.mocked(resumesApi.getATSReview).mockResolvedValue(null);
    vi.mocked(resumesApi.handleSuggestionAction).mockResolvedValue({ ...suggestion, status: 'accepted' } as never);

    render(
      <MemoryRouter initialEntries={['/resume/resume-1/enhancement']}>
        <Routes><Route path="/resume/:resumeId/enhancement" element={<ResumeDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await screen.findByRole('heading', { name: 'Resume enhancements' });
    expect(screen.queryByText('81')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Accept and save version' }));

    expect(await screen.findByRole('heading', { name: 'Your revised text draft' })).toBeTruthy();
    fireEvent.click(screen.getByText('Preview revised resume text'));
    expect(document.querySelector('pre')?.textContent).toBe('Experience\nBuilt reliable Python test suites\nEducation');
    expect(resumesApi.handleSuggestionAction).toHaveBeenCalledWith('suggestion-1', 'accept', 'Built reliable Python test suites');
  });

  it('explains the resume checklist and shows filtered suggestions as an informational note', async () => {
    vi.mocked(resumesApi.getResume).mockResolvedValue({
      id: 'resume-1', file_name: 'candidate-resume.pdf', parsing_status: 'extracted',
      analysis_status: 'analysis_completed', extraction_confidence: 0.9,
      parsed_data: { skills: ['Python', 'SQL'] },
      raw_text: 'Candidate\nEmail: candidate@example.com\nSkills\nPython, SQL\nExperience\nBuilt a service for 200 users',
      versions: [],
      analysis_error: '2 optional wording suggestion(s) were hidden because their quoted source could not be matched reliably to the extracted text. Your AI analysis and score were saved. Review the extracted-text preview or retry analysis if you expected more suggestions.',
      extraction_error: null,
    } as never);
    vi.mocked(resumesApi.getAnalysis).mockResolvedValue({
      id: 'analysis-1', resume_id: 'resume-1', status: 'analysis_completed', overall_score: 72,
      category_scores: {}, completeness_score: 0, skills_relevance_score: 0,
      experience_quality_score: 0, target_role_alignment_score: 0, formatting_score: 0,
      strengths: ['A documented service has a quantified user count.'],
      weaknesses: [], missing_keywords: ['Docker'],
      improvement_opportunities: ['Review the extracted text for spacing errors.'],
      extraction_confidence: 0.9, suggestions: [], created_at: '2026-11-20T00:00:00Z',
    } as never);
    vi.mocked(resumesApi.getATSReview).mockResolvedValue(null);

    render(
      <MemoryRouter initialEntries={['/resume/resume-1/analysis']}>
        <Routes><Route path="/resume/:resumeId/analysis" element={<ResumeDetailPage />} /></Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'Resume structure check' })).toBeTruthy();
    expect(screen.getByText(/not an ATS vendor score/)).toBeTruthy();
    expect(screen.getByRole('status').textContent).toMatch(/AI analysis and score were saved/);
    expect(screen.getByRole('status').className).toContain('bg-slate-50');
    expect(screen.getByRole('heading', { name: 'Suggested next steps' })).toBeTruthy();
    expect(screen.getByText('Role-related terms to review')).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
