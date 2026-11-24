// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { RouteErrorBoundary } from './RouteErrorBoundary';

afterEach(() => cleanup());

describe('RouteErrorBoundary', () => {
  it('shows recovery actions when a route fails to render or load', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    function BrokenRoute(): never {
      throw new Error('synthetic lazy route failure');
    }

    render(<RouteErrorBoundary><BrokenRoute /></RouteErrorBoundary>);

    expect(screen.getByRole('alert').textContent).toContain('This page couldn’t load');
    expect(screen.getByRole('button', { name: 'Reload page' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Return to overview' }).getAttribute('href')).toBe('/dashboard');
    consoleError.mockRestore();
  });
});
