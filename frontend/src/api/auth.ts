import { apiClient } from './client';
import type { User } from '../types';

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export const authApi = {
  login: async (credentials: { email: string; password: string }) => {
    return apiClient<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  },

  register: async (data: { email: string; password: string; full_name: string }) => {
    return apiClient<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  logout: async (refreshToken: string) => {
    return apiClient<{ logged_out: boolean }>('/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  changePassword: async (currentPassword: string, newPassword: string) => {
    return apiClient<{ changed: boolean }>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  },

  getMe: async () => {
    return apiClient<User>('/auth/me');
  },

  forgotPassword: async (email: string) => {
    return apiClient<{ sent: boolean }>('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },

  resetPassword: async (token: string, new_password: string) => apiClient<{ reset: boolean }>('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, new_password }),
  }),
};
