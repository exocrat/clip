// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { initializeTheme, ThemeToggle } from '../src/app/ThemeToggle';

afterEach(() => {
  cleanup();
  localStorage.clear();
  delete document.documentElement.dataset.theme;
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('theme preference', () => {
  it('applies a saved palette before the app is mounted', () => {
    localStorage.setItem('clip-theme', 'dark');
    initializeTheme();
    expect(document.documentElement.dataset.theme).toBe('dark');
  });

  it('uses the system color scheme when no preference is saved', () => {
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }));
    render(<ThemeToggle />);
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(screen.getByRole('button', { name: 'Switch to light mode' })).toBeTruthy();
  });

  it('toggles and restores the selected theme on remount', () => {
    localStorage.setItem('clip-theme', 'light');
    const view = render(<ThemeToggle />);
    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark mode' }));
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(localStorage.getItem('clip-theme')).toBe('dark');
    view.unmount();
    render(<ThemeToggle />);
    expect(screen.getByRole('button', { name: 'Switch to light mode' })).toBeTruthy();
  });

  it('continues to switch when browser storage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked'); });
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: false }));
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark mode' }));
    expect(document.documentElement.dataset.theme).toBe('dark');
  });
});
