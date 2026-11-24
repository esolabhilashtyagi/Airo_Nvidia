// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const { listResumes } = vi.hoisted(() => ({ listResumes: vi.fn() }));

vi.mock('../../api/resumes', () => ({ resumesApi: { listResumes } }));

import { ResumeLibraryPage } from './ResumeLibraryPage';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('ResumeLibraryPage', () => {
  it('keeps the Choose a resume action and removes the duplicate upload dropzone', async () => {
    listResumes.mockResolvedValue([]);
    render(<MemoryRouter><ResumeLibraryPage /></MemoryRouter>);

    expect(await screen.findByText('No resumes uploaded yet')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Choose a resume' })).toBeTruthy();
    expect(screen.queryByText(/Drop a resume here or browse files/)).toBeNull();
  });

  it('keeps an upload action available when resume history is populated', async () => {
    listResumes.mockResolvedValue([{
      id: 'resume-1', candidate_profile_id: 'profile-1', file_name: 'first.pdf', file_size_bytes: 1024,
      mime_type: 'application/pdf', sha256_hash: 'hash', parsing_status: 'extracted', analysis_status: 'pending',
      extraction_confidence: 1, parsed_data: {}, created_at: '2026-11-24T00:00:00Z', updated_at: '2026-11-24T00:00:00Z',
    }]);
    render(<MemoryRouter><ResumeLibraryPage /></MemoryRouter>);

    expect(await screen.findByText('first.pdf')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Upload another resume' })).toBeTruthy();
  });
});
