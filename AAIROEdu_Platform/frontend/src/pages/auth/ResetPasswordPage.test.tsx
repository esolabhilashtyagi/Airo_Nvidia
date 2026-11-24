// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const { resetPassword } = vi.hoisted(() => ({ resetPassword: vi.fn() }));
vi.mock('../../api/auth', () => ({ authApi: { resetPassword } }));
import { ResetPasswordPage } from './ResetPasswordPage';

afterEach(() => { cleanup(); vi.clearAllMocks(); window.history.replaceState({}, '', '/'); });

describe('ResetPasswordPage', () => {
  it('submits the fragment token once, confirms the new password, and shows success', async () => {
    window.history.replaceState({}, '', '/reset-password#token=one-time-token');
    resetPassword.mockResolvedValue({ reset: true });
    const user = userEvent.setup();
    render(<MemoryRouter initialEntries={['/reset-password']}><Routes><Route path="/reset-password" element={<ResetPasswordPage />} /></Routes></MemoryRouter>);

    const password = screen.getByLabelText('New password');
    const confirmation = screen.getByLabelText('Confirm new password');
    await user.type(password, 'StrongFreshPassword!42');
    await user.type(confirmation, 'StrongFreshPassword!42');
    await user.click(screen.getByRole('button', { name: 'Update password' }));

    expect(resetPassword).toHaveBeenCalledWith('one-time-token', 'StrongFreshPassword!42');
    expect(await screen.findByRole('heading', { name: 'Password updated' })).toBeTruthy();
  });

  it('does not call the API when confirmation does not match', async () => {
    window.history.replaceState({}, '', '/reset-password#token=one-time-token');
    render(<MemoryRouter initialEntries={['/reset-password']}><Routes><Route path="/reset-password" element={<ResetPasswordPage />} /></Routes></MemoryRouter>);
    fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'StrongFreshPassword!42' } });
    fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'DifferentPassword!42' } });
    fireEvent.click(screen.getByRole('button', { name: 'Update password' }));

    expect((await screen.findByRole('alert')).textContent).toContain('The passwords do not match.');
    expect(resetPassword).not.toHaveBeenCalled();
  });
});
