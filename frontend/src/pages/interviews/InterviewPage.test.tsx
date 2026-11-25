// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const { listIndustries, interviewHistory, setup, respond, report, conclude } = vi.hoisted(() => ({
  listIndustries: vi.fn(),
  interviewHistory: vi.fn(),
  setup: vi.fn(),
  respond: vi.fn(),
  report: vi.fn(),
  conclude: vi.fn(),
}));

vi.mock('../../api/candidates', () => ({ industriesApi: { listIndustries } }));
vi.mock('../../api/interviews', () => ({
  interviewsApi: { history: interviewHistory, setup, respond, report, conclude },
}));

import { InterviewPage } from './InterviewPage';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('InterviewPage saved answers', () => {
  it('withholds saved answers during the interview and shows refined responses after completion', async () => {
    listIndustries.mockResolvedValue([{ id: 'industry-1', name: 'Information Technology' }]);
    interviewHistory.mockResolvedValue([]);
    setup.mockResolvedValue({
      id: 'interview-1', job_role: 'AI Engineer', interview_round: 'Technical', difficulty: 'Intermediate',
      mode: 'text', status: 'in_progress', current_question_index: 1, total_questions: 2,
      interviewer_message: 'First interview prompt?', current_question_id: 'question-1', history: [], ai_status: 'question_bank',
    });
    respond.mockResolvedValueOnce({
      id: 'interview-1', job_role: 'AI Engineer', interview_round: 'Technical', difficulty: 'Intermediate',
      mode: 'text', status: 'in_progress', current_question_index: 2, total_questions: 2,
      interviewer_message: 'Next interview prompt?', current_question_id: 'question-2',
      history: [{ q: 'PRIVATE_QUESTION_TEXT', a: 'Saved candidate answer text' }], ai_status: 'question_bank',
    });
    respond.mockResolvedValueOnce({
      id: 'evaluation-1', mock_interview_id: 'interview-1', overall_score: 82, evaluation_status: 'evaluated', evaluation_provenance: 'ai',
      key_strengths: [], improvement_areas: [], detailed_feedback: {}, question_evaluations: [],
      responses: [
        { question_number: 1, question: 'PRIVATE_QUESTION_TEXT', candidate_answer: 'Saved candidate answer text', refined_answer: 'A clear, fact-preserving final response.' },
        { question_number: 2, question: 'Next interview prompt?', candidate_answer: 'Second candidate answer text', refined_answer: 'A refined second answer.' },
      ],
    });
    const user = userEvent.setup();
    render(<InterviewPage />);

    await screen.findByRole('option', { name: 'Information Technology' });
    await user.selectOptions(screen.getByRole('combobox', { name: /Industry/ }), 'industry-1');
    await user.selectOptions(screen.getByRole('combobox', { name: /Interview round/ }), 'Technical');
    await user.type(await screen.findByRole('textbox', { name: /Target role/ }), 'AI Engineer');
    await user.click(screen.getByRole('button', { name: 'Start interview' }));
    await user.type(await screen.findByRole('textbox', { name: /Your answer/ }), 'Saved candidate answer text');
    await user.click(screen.getByRole('button', { name: 'Save answer and continue' }));

    expect(await screen.findByText('Next interview prompt?')).toBeTruthy();
    expect(screen.queryByText('Saved candidate answer text')).toBeNull();
    expect(screen.queryByText('PRIVATE_QUESTION_TEXT')).toBeNull();
    expect(screen.queryByText(/Saved answer/)).toBeNull();

    await user.type(screen.getByRole('textbox', { name: /Your answer/ }), 'Second candidate answer text');
    await user.click(screen.getByRole('button', { name: 'Save answer and continue' }));

    expect(await screen.findByText('Final response review')).toBeTruthy();
    expect(screen.getByText('PRIVATE_QUESTION_TEXT')).toBeTruthy();
    expect(screen.getByText('Saved candidate answer text')).toBeTruthy();
    expect(screen.getByText('A clear, fact-preserving final response.')).toBeTruthy();
  });
});
