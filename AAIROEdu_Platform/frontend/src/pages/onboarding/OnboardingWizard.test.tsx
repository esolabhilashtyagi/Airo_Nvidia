// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

const { saveOnboardingStep, listIndustries, searchCompanies, refreshProfile } = vi.hoisted(() => ({
  saveOnboardingStep: vi.fn(),
  listIndustries: vi.fn(),
  searchCompanies: vi.fn(),
  refreshProfile: vi.fn(),
}));

vi.mock('../../api/candidates', () => ({
  candidatesApi: { saveOnboardingStep },
  industriesApi: { listIndustries },
  companiesApi: { search: searchCompanies },
}));
vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ profile: null, refreshProfile }),
}));

import { OnboardingWizard } from './OnboardingWizard';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
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
});
