import React, { createContext, useContext, useEffect, useState } from 'react';
import { authApi } from '../api/auth';
import { candidatesApi } from '../api/candidates';
import type { CandidateProfile, User } from '../types';

interface AuthContextType {
  user: User | null;
  profile: CandidateProfile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchCurrentUser = async () => {
    const token = localStorage.getItem('aairo_access_token');
    if (!token) {
      setUser(null);
      setProfile(null);
      return;
    }

    try {
      const u = await authApi.getMe();
      const candidateProfile = u.role === 'candidate'
        ? await candidatesApi.getProfile()
        : null;
      setProfile(candidateProfile);
      setUser(u);
    } catch (err) {
      localStorage.removeItem('aairo_access_token');
      localStorage.removeItem('aairo_refresh_token');
      setUser(null);
      setProfile(null);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // A browser-stored session must never sign a candidate in without a fresh credential submission.
    localStorage.removeItem('aairo_access_token');
    localStorage.removeItem('aairo_refresh_token');
  }, []);

  const login = async (email: string, pass: string) => {
    setIsLoading(true);
    setUser(null);
    setProfile(null);
    localStorage.removeItem('aairo_access_token');
    localStorage.removeItem('aairo_refresh_token');
    try {
      const tokens = await authApi.login({ email, password: pass });
      localStorage.setItem('aairo_access_token', tokens.access_token);
      localStorage.setItem('aairo_refresh_token', tokens.refresh_token);
      await fetchCurrentUser();
    } catch (err) {
      localStorage.removeItem('aairo_access_token');
      localStorage.removeItem('aairo_refresh_token');
      setUser(null);
      setProfile(null);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, pass: string, name: string) => {
    await authApi.register({ email, password: pass, full_name: name });
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem('aairo_refresh_token');
    try {
      if (refreshToken) await authApi.logout(refreshToken);
    } catch {
      // Always clear the local session even if the server is unreachable.
    } finally {
      localStorage.removeItem('aairo_access_token');
      localStorage.removeItem('aairo_refresh_token');
      setUser(null);
      setProfile(null);
      window.location.href = '/login';
    }
  };

  const refreshProfile = async () => {
    if (user?.role === 'candidate') {
      const p = await candidatesApi.getProfile();
      setProfile(p);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
