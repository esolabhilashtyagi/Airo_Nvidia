import { API_BASE, ApiError, apiClient } from './client';
import type { Resume, ResumeAnalysis, ResumeATSReview, ResumeDetail, ResumeParsedData, ResumeSuggestion, ResumeVersion } from '../types';

export const resumesApi = {
  generateFromProfile: async (template: 'standard' | 'modern' | 'classic' | 'compact' = 'standard', format: 'pdf' | 'docx' = 'pdf') => {
    const token = localStorage.getItem('aairo_access_token');
    const response = await fetch(`${API_BASE}/resumes/generate-from-profile?template=${template}&format=${format}`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = body?.error?.message || body?.detail;
      const message = typeof detail === 'string' ? detail : 'Your profile resume could not be generated.';
      throw new ApiError(message, body?.error?.code || 'RESUME_GENERATION_FAILED');
    }
    const filename = response.headers.get('Content-Disposition')?.match(/filename="?([^";]+)"?/i)?.[1] || `aairo-resume.${format}`;
    return { blob: await response.blob(), filename };
  },

  uploadResume: async (file: File, onProgress?: (progress: number, stage: 'uploading' | 'processing') => void) => {
    const formData = new FormData();
    formData.append('file', file);
    return new Promise<Resume>((resolve, reject) => {
      const request = new XMLHttpRequest();
      request.open('POST', `${API_BASE}/resumes/upload`);
      const token = localStorage.getItem('aairo_access_token');
      if (token) request.setRequestHeader('Authorization', `Bearer ${token}`);
      request.upload.addEventListener('progress', (event) => {
        if (!event.lengthComputable || event.total <= 0) return;
        const uploadedPercent = Math.max(0, Math.min(100, Math.round((event.loaded / event.total) * 100)));
        onProgress?.(uploadedPercent, uploadedPercent === 100 ? 'processing' : 'uploading');
      });
      request.upload.addEventListener('load', () => onProgress?.(100, 'processing'));
      request.addEventListener('load', () => {
        let body: any = null;
        try {
          body = request.responseText ? JSON.parse(request.responseText) : null;
        } catch {
          reject(new ApiError('The server returned an unreadable upload response.', 'INVALID_RESPONSE'));
          return;
        }
        if (request.status >= 200 && request.status < 300) {
          onProgress?.(100, 'processing');
          resolve(body?.data ?? body);
        } else {
          reject(new ApiError(body?.error?.message || body?.detail || 'Resume upload failed.', body?.error?.code || 'UPLOAD_FAILED'));
        }
      });
      request.addEventListener('error', () => reject(new ApiError('Network error while uploading the resume.')));
      request.send(formData);
    });
  },

  listResumes: async () => {
    return apiClient<Resume[]>('/resumes');
  },

  getResume: async (resumeId: string) => apiClient<ResumeDetail>(`/resumes/${resumeId}`),

  extractResume: async (resumeId: string) => apiClient<ResumeDetail>(`/resumes/${resumeId}/extract`, { method: 'POST' }),

  updateParsedData: async (resumeId: string, parsed_data: ResumeParsedData) => apiClient<ResumeDetail>(`/resumes/${resumeId}/parsed-data`, {
    method: 'PUT', body: JSON.stringify({ parsed_data }),
  }),

  listVersions: async (resumeId: string) => apiClient<ResumeVersion[]>(`/resumes/${resumeId}/versions`),

  getAnalysis: async (resumeId: string) => apiClient<ResumeAnalysis | null>(`/resumes/${resumeId}/analysis`),

  getATSReview: async (resumeId: string) => apiClient<ResumeATSReview | null>(`/resumes/${resumeId}/ats-review`),

  extractJobDescription: async (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return apiClient<string>('/resumes/job-description/extract', { method: 'POST', body: form });
  },

  createATSReview: async (resumeId: string, job_title: string, job_description: string) => apiClient<ResumeATSReview>(`/resumes/${resumeId}/ats-review`, {
    method: 'POST', body: JSON.stringify({ job_title, job_description }),
  }),

  analyzeResume: async (resumeId: string, job?: { job_title: string; job_description: string }) => {
    return apiClient<ResumeAnalysis>(`/resumes/${resumeId}/analyze`, {
      method: 'POST',
      ...(job ? { body: JSON.stringify(job) } : {}),
    });
  },

  enhanceResume: async (resumeId: string) => apiClient<ResumeAnalysis>(`/resumes/${resumeId}/enhance`, { method: 'POST' }),

  handleSuggestionAction: async (suggestionId: string, action: 'accept' | 'reject', edited_text?: string) => {
    return apiClient<ResumeSuggestion>(`/resumes/suggestions/${suggestionId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action, edited_text }),
    });
  },

  deleteResume: async (resumeId: string) => apiClient<void>(`/resumes/${resumeId}`, { method: 'DELETE' }),
};
