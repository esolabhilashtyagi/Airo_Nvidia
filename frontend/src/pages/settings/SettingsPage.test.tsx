// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: { full_name: 'Aishwarya', email: 'aishwarya@example.com' } }),
}));

import { SettingsPage } from './SettingsPage';

afterEach(() => cleanup());

describe('SettingsPage', () => {
  it('keeps signed-in password changes distinct from forgotten-password recovery', () => {
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);

    expect(screen.getByRole('heading', { name: 'Settings' })).toBeTruthy();
    expect(screen.getByText('Aishwarya')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Change password' })).toBeTruthy();
    expect(screen.getByText(/Use this while signed in and you know your current password/)).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Request reset instructions' }).getAttribute('href')).toBe('/forgot-password');
  });
});
