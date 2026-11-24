// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import { Sidebar } from './components/common/Sidebar';
import { MemoryRouter } from 'react-router-dom';

afterEach(() => {
  cleanup();
  window.history.replaceState({}, '', '/');
  localStorage.clear();
});

describe('application routes', () => {
  it('renders the sign-in screen and navigates to registration', async () => {
    window.history.replaceState({}, '', '/login');
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Sign in to your account' })).toBeTruthy();
    await user.click(screen.getByRole('link', { name: 'Create free account' }));
    expect(await screen.findByRole('heading', { name: 'Create candidate account' })).toBeTruthy();
  });

  it('requires manually entered credentials and does not offer demo account login', async () => {
    window.history.replaceState({}, '', '/login');
    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Sign in to your account' })).toBeTruthy();
    expect((screen.getByPlaceholderText('candidate@aairo.ai') as HTMLInputElement).value).toBe('');
    expect((screen.getByPlaceholderText('••••••••••••') as HTMLInputElement).value).toBe('');
    expect(screen.queryByRole('button', { name: 'Candidate' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Admin' })).toBeNull();
  });

  it('creates an account without signing in until credentials are entered manually', async () => {
    window.history.replaceState({}, '', '/register');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      data: { id: 'candidate-id', email: 'new@example.com', full_name: 'New Candidate', role: 'candidate' },
    }), { status: 201, headers: { 'Content-Type': 'application/json' } }));
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole('heading', { name: 'Create candidate account' });
    await user.type(screen.getByPlaceholderText('e.g. Maya Patel'), 'New Candidate');
    await user.type(screen.getByPlaceholderText('candidate@example.com'), 'new@example.com');
    await user.type(screen.getByPlaceholderText('8+ characters; avoid common passwords'), 'ZzNewCandidate785!');
    await user.click(screen.getByRole('button', { name: 'Create Account' }));

    expect(await screen.findByText('Account created. Enter your email and password to sign in.')).toBeTruthy();
    expect((screen.getByPlaceholderText('candidate@aairo.ai') as HTMLInputElement).value).toBe('new@example.com');
    expect((screen.getByPlaceholderText('••••••••••••') as HTMLInputElement).value).toBe('');
    expect((screen.getByPlaceholderText('••••••••••••') as HTMLInputElement).autocomplete).toBe('new-password');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain('/auth/register');
    expect(localStorage.getItem('aairo_access_token')).toBeNull();
  });

  it('requires authentication before showing the dashboard', async () => {
    window.history.replaceState({}, '', '/dashboard');
    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Sign in to your account' })).toBeTruthy();
  });

  it('clears saved tokens and does not automatically restore an earlier account', async () => {
    window.history.replaceState({}, '', '/dashboard');
    localStorage.setItem('aairo_access_token', 'previous-account-token');
    localStorage.setItem('aairo_refresh_token', 'previous-account-refresh-token');
    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Sign in to your account' })).toBeTruthy();
    expect(localStorage.getItem('aairo_access_token')).toBeNull();
    expect(localStorage.getItem('aairo_refresh_token')).toBeNull();
  });

  it('renders the sidebar under the shared auth provider without hook errors', () => {
    render(
      <AuthProvider>
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      </AuthProvider>,
    );

    expect(screen.getByText('Preparation Suite')).toBeTruthy();
    expect(screen.getByRole('link', { name: /Overview/ })).toBeTruthy();
  });
});
