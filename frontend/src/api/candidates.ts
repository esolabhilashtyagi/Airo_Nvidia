import { apiClient } from './client';
import type { CandidateProfile, Industry } from '../types';

export const candidatesApi = {
  getProfile: async () => {
    return apiClient<CandidateProfile>('/candidates/profile');
  },

  saveOnboardingStep: async (stepData: any) => {
    return apiClient<CandidateProfile>('/candidates/onboarding/step', {
      method: 'POST',
      body: JSON.stringify(stepData),
    });
  },
};

export const industriesApi = {
  listIndustries: async () => {
    return apiClient<Industry[]>('/industries');
  },
  getIndustry: async (id: string) => {
    return apiClient<Industry>(`/industries/${id}`);
  },
};

export const companiesApi = {
  search: async (search: string) => {
    const query = new URLSearchParams({ search, limit: '20' });
    return apiClient<{ id: string; name: string }[]>(`/companies?${query.toString()}`);
  },
};
