import { apiClient } from './client';
import type {
  AssessmentAttempt, AssessmentResult, DashboardOverview,
  InterviewReport, MockInterviewSession, Module, Question, QuestionPracticeHistory, Roadmap,
  CompanyInterviewQuestion, CompanySummary, CompanyBlueprint
} from '../types';

export const systemApi = {
  getAiStatus: async () => apiClient<{ provider: string; model: string; configured: boolean }>('/system/ai-status'),
  getNotifications: async () => apiClient<Array<{ id: string; title: string; message: string; type: string; is_read: boolean; link_url?: string | null; created_at: string }>>('/system/notifications'),
  markNotificationRead: async (id: string) => apiClient<{ id: string; is_read: boolean }>(`/system/notifications/${id}/read`, { method: 'PATCH' }),
};

export const questionsApi = {
  listQuestions: async (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') query.append(k, String(v));
    });
    return apiClient<Question[]>(`/questions?${query.toString()}`);
  },

  taxonomy: async () => apiClient<{
    categories: Array<{ id: string; name: string }>;
    job_roles: Array<{ id: string; title: string }>;
    subjects: Array<{ id: string; name: string }>;
    topics: Array<{ id: string; name: string; subject_id: string }>;
    skills: Array<{ id: string; name: string }>;
    experience_levels: Array<{ id: string; name: string }>;
    interview_rounds: Array<{ id: string; name: string }>;
    companies: Array<{ id: string; name: string }>;
  }>('/question-taxonomy'),
  history: async (page = 1, limit = 20) => apiClient<QuestionPracticeHistory[]>(`/questions/history?page=${page}&limit=${limit}`),

  getQuestion: async (id: string) => {
    return apiClient<Question>(`/questions/${id}`);
  },

  toggleBookmark: async (id: string) => {
    return apiClient<{ is_bookmarked: boolean }>(`/questions/${id}/bookmark`, {
      method: 'POST',
    });
  },

  practiceQuestion: async (id: string, user_response: string) => {
    return apiClient<import('../types').QuestionPracticeResult>(`/questions/${id}/practice`, {
      method: 'POST',
      body: JSON.stringify({ user_response }),
    });
  },

  manage: async (params: Record<string, string | number | null | undefined> = {}) => {
    const query = new URLSearchParams();
    const filters: Record<string, unknown> = { page: 1, limit: 50, ...params };
    Object.entries(filters).forEach(([key, value]) => {
      if (value === undefined || value === null || (typeof value === 'string' && value.length === 0)) return;
      query.set(key, String(value));
    });
    return apiClient<Question[]>(`/questions/manage?${query.toString()}`);
  },

  create: async (payload: Record<string, unknown>) => apiClient<Question>('/questions', {
    method: 'POST', body: JSON.stringify(payload),
  }),

  generateDraft: async (payload: Record<string, unknown>) => apiClient<Question>('/questions/manage/ai-draft', {
    method: 'POST', body: JSON.stringify(payload),
  }),

  review: async (id: string, decision: 'approved' | 'rejected') => apiClient<Question>(`/questions/manage/${id}/review`, {
    method: 'POST', body: JSON.stringify({ decision }),
  }),

  submitForReview: async (id: string) => apiClient<Question>(`/questions/manage/${id}/submit`, { method: 'POST' }),
  publish: async (id: string) => apiClient<Question>(`/questions/manage/${id}/publish`, { method: 'POST' }),
  versions: async (id: string) => apiClient<Question[]>(`/questions/manage/${id}/versions`),
  restoreVersion: async (id: string, versionId: string) => apiClient<Question>(`/questions/manage/${id}/restore/${versionId}`, { method: 'POST' }),

  archive: async (id: string) => apiClient<void>(`/questions/manage/${id}`, { method: 'DELETE' }),
};

export const companyIntelApi = {
  listQuestions: async (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') query.append(k, String(v));
    });
    return apiClient<CompanyInterviewQuestion[]>(`/questions/company-intel?${query.toString()}`);
  },

  listCompanies: async () => apiClient<CompanySummary[]>('/questions/company-intel/companies'),

  getBlueprint: async (companyName: string, role = 'Software Development Engineer', yoe = 3.5) =>
    apiClient<CompanyBlueprint>(`/questions/company-intel/blueprint/${encodeURIComponent(companyName)}?role=${encodeURIComponent(role)}&yoe=${yoe}`),

  getQuestion: async (id: string) => apiClient<CompanyInterviewQuestion>(`/questions/company-intel/${id}`),

  practiceQuestion: async (question_id: string, user_response: string) =>
    apiClient<import('../types').QuestionPracticeResult>('/questions/company-intel/practice', {
      method: 'POST',
      body: JSON.stringify({ question_id, user_response }),
    }),

  generateDorks: async (payload: { company: string; role?: string; yoe?: number; skills?: string[] }) =>
    apiClient<import('../types').DynamicDorks>('/questions/company-intel/generate-dorks', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  synthesizeRoundQuestions: async (payload: { company: string; role?: string; yoe?: number; round_number?: number; skills?: string[] }) =>
    apiClient<import('../types').SynthesizedRoundQuestion[]>('/questions/company-intel/round-questions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  triggerLiveScrape: async (payload: { company: string; role?: string; keyword?: string; limit?: number; max_pages?: number }) =>
    apiClient<any>('/questions/company-intel/live-scrape', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

export const questionTaxonomyApi = {
  list: async (kind: string, search = '', filters: { industry_id?: string; parent_id?: string } = {}) => {
    const query = new URLSearchParams({ page: '1', limit: '100', search });
    if (filters.industry_id) query.set('industry_id', filters.industry_id);
    if (filters.parent_id) query.set('parent_id', filters.parent_id);
    return apiClient<Array<Record<string, any>>>(`/question-taxonomy/manage/${kind}?${query}`);
  },
  create: async (payload: Record<string, unknown>) => apiClient<Record<string, any>>('/question-taxonomy/manage', { method: 'POST', body: JSON.stringify(payload) }),
  update: async (kind: string, id: string, payload: Record<string, unknown>) => apiClient<Record<string, any>>(`/question-taxonomy/manage/${kind}/${id}`, { method: 'PATCH', body: JSON.stringify({ ...payload, kind }) }),
  deactivate: async (kind: string, id: string) => apiClient<Record<string, any>>(`/question-taxonomy/manage/${kind}/${id}`, { method: 'DELETE' }),
  setActive: async (kind: string, id: string, active: boolean) => apiClient<Record<string, any>>(`/question-taxonomy/manage/${kind}/${id}/active?active=${active}`, { method: 'PATCH' }),
};

export const modulesApi = {
  manage: async () => apiClient<Module[]>('/modules/manage'),
  createDraft: async (data: Record<string, unknown>) => apiClient<Module>('/modules/manage', { method: 'POST', body: JSON.stringify(data) }),
  updateManaged: async (id: string, data: Record<string, unknown>) => apiClient<Module>(`/modules/manage/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  addLesson: async (id: string, data: Record<string, unknown>) => apiClient(`/modules/manage/${id}/lessons`, { method: 'POST', body: JSON.stringify(data) }),
  updateLesson: async (moduleId: string, lessonId: string, data: Record<string, unknown>) => apiClient(`/modules/manage/${moduleId}/lessons/${lessonId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  archiveLesson: async (moduleId: string, lessonId: string) => apiClient(`/modules/manage/${moduleId}/lessons/${lessonId}`, { method: 'DELETE' }),
  deleteManaged: async (id: string) => apiClient<void>(`/modules/manage/${id}`, { method: 'DELETE' }),
  listModules: async () => {
    return apiClient<Module[]>('/modules');
  },

  getModuleDetail: async (id: string) => {
    return apiClient<Module>(`/modules/${id}`);
  },

  enroll: async (id: string) => apiClient<Module>(`/modules/${id}/enroll`, { method: 'POST' }),

  completeLesson: async (moduleId: string, lessonId: string) => {
    return apiClient<Module>(`/modules/${moduleId}/lessons/${lessonId}/complete`, {
      method: 'POST',
    });
  },

  getActiveRoadmap: async () => {
    return apiClient<Roadmap | null>('/modules/roadmap/active');
  },

  toggleRoadmapTask: async (taskId: string) => {
    return apiClient<any>(`/modules/roadmap/tasks/${taskId}/toggle`, {
      method: 'POST',
    });
  },
};

export const coachApi = {
  getSkillGap: async () => {
    return apiClient<{
      strong_skills: string[];
      weak_skills: string[];
      missing_skills: string[];
      technical_gaps: string[];
      domain_gaps: string[];
      self_reported_skills: string[];
      skill_evidence: Record<string, string>;
      evidence_sources: string[];
      learning_priorities: any[];
      coach_summary: string;
      ai_status: string;
    }>('/coach/skill-gap');
  },

  generateRoadmap: async () => {
    return apiClient<Roadmap>('/coach/roadmap/generate', {
      method: 'POST',
    });
  },

  chat: async (message: string, conversation_id?: string) => {
    return apiClient<{
      conversation_id: string;
      reply: string | null;
      suggested_actions: string[];
      ai_status: string;
    }>('/coach/chat', {
      method: 'POST',
      body: JSON.stringify({ message, conversation_id }),
    });
  },
  listConversations: async () => apiClient<Array<{ id: string; title: string; updated_at: string }>>('/coach/conversations'),
  getConversation: async (id: string) => apiClient<{
    id: string;
    title: string;
    messages: Array<{ id: string; sender: 'user' | 'assistant' | 'system'; message_text: string; created_at: string }>;
  }>(`/coach/conversations/${id}`),
};

export const testingApi = {
  configure: async (config: any) => {
    return apiClient<any>('/testing/configure', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  },

  startAssessment: async (assessmentId: string) => {
    return apiClient<{
      attempt_id: string;
      assessment_id: string;
      title: string;
      duration_minutes: number;
      total_questions: number;
      started_at: string;
      ends_at: string;
      questions: Question[];
      saved_answers: Array<{ question_id: string; selected_options: string[]; text_response?: string | null; is_marked_for_review: boolean }>;
    }>(`/testing/${assessmentId}/start`, {
      method: 'POST',
    });
  },

  saveAnswer: async (attemptId: string, answerData: any) => {
    return apiClient<any>(`/testing/attempts/${attemptId}/save-answer`, {
      method: 'POST',
      body: JSON.stringify(answerData),
    });
  },

  submitAssessment: async (attemptId: string) => {
    return apiClient<AssessmentResult>(`/testing/attempts/${attemptId}/submit`, {
      method: 'POST',
    });
  },

  getHistory: async () => {
    return apiClient<AssessmentAttempt[]>('/testing/history');
  },

  getResult: async (attemptId: string) => apiClient<AssessmentResult>(`/testing/attempts/${attemptId}/results`),
};

export const interviewsApi = {
  setup: async (config: any) => {
    return apiClient<MockInterviewSession>('/interviews/setup', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  },

  respond: async (interviewId: string, candidate_answer: string, duration_seconds = 0) => {
    return apiClient<MockInterviewSession | InterviewReport>(`/interviews/${interviewId}/respond`, {
      method: 'POST',
      body: JSON.stringify({ candidate_answer, duration_seconds }),
    });
  },

  conclude: async (interviewId: string) => {
    return apiClient<InterviewReport>(`/interviews/${interviewId}/conclude`, {
      method: 'POST',
    });
  },

  getReport: async (interviewId: string) => {
    return apiClient<InterviewReport>(`/interviews/${interviewId}/report`);
  },
};

export const dashboardApi = {
  getOverview: async () => {
    return apiClient<DashboardOverview>('/dashboard/overview');
  },

  getAnalytics: async () => {
    return apiClient<any>('/dashboard/analytics');
  },
};

export const adminApi = {
  getStats: async () => {
    return apiClient<any>('/admin/stats');
  },

  listUsers: async () => {
    return apiClient<any[]>('/admin/users');
  },
  setUserActive: async (id: string, isActive: boolean) => {
    return apiClient<any>(`/admin/users/${id}/active`, { method: 'PATCH', body: JSON.stringify({ is_active: isActive }) });
  },
};
