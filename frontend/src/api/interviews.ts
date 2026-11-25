import { apiClient } from './client';

export interface InterviewSession {
  id: string; job_role: string; target_company?: string | null; interview_round: string;
  difficulty: string; mode: string; status: string; started_at?: string | null;
  current_question_index: number; total_questions: number; interviewer_message?: string | null;
  current_question_id?: string | null; history: Array<{ q: string; a: string }>;
  ai_status: 'question_bank' | 'ai_generated' | 'unavailable' | string;
}
export interface InterviewReport {
  id: string; mock_interview_id: string; overall_score?: number | null;
  technical_score?: number | null; domain_score?: number | null; communication_score?: number | null;
  structure_score?: number | null; evaluation_status: string; evaluation_provenance: string;
  key_strengths: string[]; improvement_areas: string[]; detailed_feedback: Record<string, unknown>;
  question_evaluations: Array<Record<string, unknown>>; completed_at?: string | null;
  responses: Array<{
    question_number: number;
    question: string;
    candidate_answer: string;
    refined_answer?: string | null;
  }>;
}
export const interviewsApi = {
  setup: (data: Record<string, unknown>) => apiClient<InterviewSession>('/interviews/setup', { method: 'POST', body: JSON.stringify(data) }),
  session: (id: string) => apiClient<InterviewSession>(`/interviews/${id}`),
  respond: (id: string, candidate_answer: string) => apiClient<InterviewSession | InterviewReport>(`/interviews/${id}/respond`, { method: 'POST', body: JSON.stringify({ candidate_answer }) }),
  conclude: (id: string) => apiClient<InterviewReport>(`/interviews/${id}/conclude`, { method: 'POST' }),
  report: (id: string) => apiClient<InterviewReport>(`/interviews/${id}/report`),
  history: () => apiClient<Array<Record<string, unknown>>>('/interviews/history'),
};
