// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

const { coachApi, modulesApi } = vi.hoisted(() => ({
  coachApi: {
    getSkillGap: vi.fn(), listConversations: vi.fn(), getConversation: vi.fn(), chat: vi.fn(),
    generateRoadmap: vi.fn(),
  },
  modulesApi: { getActiveRoadmap: vi.fn(), toggleRoadmapTask: vi.fn() },
}));

vi.mock('../../api/services', () => ({ coachApi, modulesApi }));
vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ profile: { target_role: 'Software Engineer' } }),
}));
import { CoachPage } from './CoachPage';

afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe('CoachPage conversation flow', () => {
  it('keeps the coaching workspace loaded when a new conversation is created', async () => {
    coachApi.getSkillGap.mockResolvedValue({
      strong_skills: [], weak_skills: [], missing_skills: [], technical_gaps: [], domain_gaps: [],
      self_reported_skills: [], skill_evidence: {}, evidence_sources: [], learning_priorities: [],
      coach_summary: 'Profile-based coaching summary', ai_status: 'unavailable',
    });
    modulesApi.getActiveRoadmap.mockResolvedValue(null);
    coachApi.listConversations.mockResolvedValueOnce([]).mockResolvedValueOnce([
      { id: 'conversation-1', title: 'hi', updated_at: '2026-11-20T00:00:00Z' },
    ]);
    coachApi.chat.mockResolvedValue({ conversation_id: 'conversation-1', reply: 'Hello! What role are you working toward?', ai_status: 'ai_generated', suggested_actions: [] });
    coachApi.getConversation.mockResolvedValue({ id: 'conversation-1', title: 'hi', messages: [
      { id: 'message-1', sender: 'user', message_text: 'hi', created_at: '2026-11-20T00:00:00Z' },
      { id: 'message-2', sender: 'assistant', message_text: 'Hello! **What role** are you working toward?\n1. **First step**\n2. Second step', created_at: '2026-11-20T00:00:01Z' },
    ] });

    const user = userEvent.setup();
    render(<MemoryRouter><CoachPage /></MemoryRouter>);
    await screen.findByText('Profile-based coaching summary');
    await user.type(screen.getByRole('textbox', { name: 'Message the coach' }), 'hi');
    await user.click(screen.getByRole('button', { name: 'Send message' }));

    expect(await screen.findByText('What role')).toBeTruthy();
    expect(screen.queryByText('Top learning resources')).toBeNull();
    expect(screen.getByText('What role').tagName).toBe('STRONG');
    expect(screen.getByText('First step').closest('ol')).toBeTruthy();
    expect(screen.queryByText(/\*\*What role\*\*/)).toBeNull();
    expect(screen.getByLabelText('Message the coach').className).toContain('w-full');
    expect(screen.queryByText('Loading your coaching workspace…')).toBeNull();
    expect(coachApi.getSkillGap).toHaveBeenCalledTimes(1);
    expect(modulesApi.getActiveRoadmap).toHaveBeenCalledTimes(1);
  });
});
