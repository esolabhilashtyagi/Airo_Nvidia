// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

const { saveOnboardingStep, listIndustries, searchCompanies, refreshProfile, authProfile } = vi.hoisted(() => ({
  saveOnboardingStep: vi.fn(),
  listIndustries: vi.fn(),
  searchCompanies: vi.fn(),
  refreshProfile: vi.fn(),
  authProfile: { current: null as any },
}));

vi.mock('../../api/candidates', () => ({
  candidatesApi: { saveOnboardingStep },
  industriesApi: { listIndustries },
  companiesApi: { search: searchCompanies },
}));
vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ profile: authProfile.current, refreshProfile }),
}));

import { OnboardingWizard } from './OnboardingWizard';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  authProfile.current = null;
});

describe('OnboardingWizard', () => {
  it('saves step one without sending an empty UUID and blocks industry step if options are missing', async () => {
    listIndustries.mockResolvedValue([]);
    saveOnboardingStep.mockResolvedValue({});
    searchCompanies.mockResolvedValue([]);
    const user = userEvent.setup();
    render(<MemoryRouter><OnboardingWizard /></MemoryRouter>);

    await user.click(await screen.findByRole('button', { name: /Save & Continue/ }));

    expect(saveOnboardingStep).toHaveBeenCalledWith(expect.objectContaining({ step: 1, industry_id: null }));
    expect(await screen.findByText('Step 2 of 7')).toBeTruthy();
    expect(screen.getByText(/No active industries are available/)).toBeTruthy();

    await user.click(screen.getByRole('button', { name: /Save & Continue/ }));
    expect(saveOnboardingStep).toHaveBeenCalledOnce();
    expect(screen.getByText(/Retry loading the options/)).toBeTruthy();
  });

  it('does not prefill the legacy Associate fallback as the candidate target role', async () => {
    authProfile.current = { onboarding_step: 4, onboarding_completed: false, candidate_type: 'student_fresher', target_role: 'Associate' };
    listIndustries.mockResolvedValue([]);
    const user = userEvent.setup();
    render(<MemoryRouter><OnboardingWizard /></MemoryRouter>);

    const targetRole = await screen.findByPlaceholderText('e.g. Senior Software Architect') as HTMLInputElement;
    expect(targetRole.value).toBe('');

    await user.click(screen.getByRole('button', { name: /Save & Continue/ }));
    expect(screen.getByText(/Enter the specific job role/)).toBeTruthy();
    expect(saveOnboardingStep).not.toHaveBeenCalled();
  });

  it('lets candidates choose a suggested company while typing and saves the selection', async () => {
    authProfile.current = { onboarding_step: 6, onboarding_completed: false, candidate_type: 'student_fresher', target_role: 'Data Scientist', target_companies: [] };
    listIndustries.mockResolvedValue([]);
    searchCompanies.mockResolvedValue([{ id: 'company-1', name: 'Example Research Labs' }]);
    saveOnboardingStep.mockResolvedValue({});
    refreshProfile.mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<MemoryRouter><OnboardingWizard /></MemoryRouter>);

    const companyInput = await screen.findByLabelText('Search or add a company');
    await user.type(companyInput, 'Example');
    await user.click(await screen.findByRole('button', { name: 'Example Research Labs' }));
    await user.click(screen.getByRole('button', { name: /Save & Continue/ }));

    expect(saveOnboardingStep).toHaveBeenCalledWith(expect.objectContaining({
      target_companies: [{ company_name: 'Example Research Labs', target_role: 'Data Scientist' }],
    }));
  });

  it('shows search failures instead of offering an existing company as new', async () => {
    authProfile.current = { onboarding_step: 6, onboarding_completed: false, candidate_type: 'student_fresher', target_companies: [] };
    listIndustries.mockResolvedValue([]);
    searchCompanies.mockRejectedValue(new Error('Service unavailable'));
    const user = userEvent.setup();
    render(<MemoryRouter><OnboardingWizard /></MemoryRouter>);

    await user.type(await screen.findByLabelText('Search or add a company'), 'Google');

    expect((await screen.findByRole('alert')).textContent).toMatch(/Service unavailable/);
    expect(screen.queryByRole('button', { name: /Add “Google” as a new company/ })).toBeNull();
  });
});
