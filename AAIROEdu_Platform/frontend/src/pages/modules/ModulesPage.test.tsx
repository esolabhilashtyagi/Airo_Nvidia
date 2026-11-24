// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom';
import { modulesApi } from '../../api/services';
import { ModulesPage } from './ModulesPage';

vi.mock('../../api/services', () => ({
  modulesApi: {
    listModules: vi.fn(),
    completeLesson: vi.fn(),
    enroll: vi.fn(),
  },
}));

afterEach(() => cleanup());

const modules = [
  { id: 'module-1', title: 'First module', description: 'First description', difficulty: 'Beginner', duration_minutes: 10, completion_percentage: 0, progress_status: 'not_started', lessons: [], completed_lesson_ids: [] },
  { id: 'module-2', title: 'Second module', description: 'Second description', difficulty: 'Intermediate', duration_minutes: 20, completion_percentage: 0, progress_status: 'not_started', lessons: [], completed_lesson_ids: [] },
] as never;

describe('ModulesPage deep links', () => {
  it('selects the module when its query parameter changes in the current session', async () => {
    vi.mocked(modulesApi.listModules).mockResolvedValue(modules);

    render(
      <MemoryRouter initialEntries={['/modules']}>
        <Link to="/modules?moduleId=module-2">Open second module</Link>
        <Routes><Route path="/modules" element={<ModulesPage />} /></Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'First module' })).toBeTruthy();
    fireEvent.click(screen.getByRole('link', { name: 'Open second module' }));

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Second module' })).toBeTruthy());
    expect(modulesApi.listModules).toHaveBeenCalledTimes(2);
  });
});
