// @vitest-environment jsdom
import { fireEvent, render, screen, cleanup } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MultiChoiceDropdown } from '../src/shared/ui/MultiChoiceDropdown';

afterEach(cleanup);

describe('multi-choice dismissal', () => {
  it('closes outside or on Escape while retaining selected values', () => {
    const change = vi.fn();
    render(<MultiChoiceDropdown label="Category" options={[{ value: 'books', label: 'Books' }]}
      values={['books']} onValuesChange={change} />);
    const summary = screen.getByText('Category').closest('summary');
    const details = summary?.closest('details');
    if (!details || !summary) throw new Error('Missing native dropdown');
    details.open = true;
    fireEvent.pointerDown(screen.getByRole('checkbox'));
    expect(details.open).toBe(true);
    fireEvent.pointerDown(document.body);
    expect(details.open).toBe(false);
    details.open = true;
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(details.open).toBe(false);
    expect(document.activeElement).toBe(summary);
    expect((screen.getByRole('checkbox', { hidden: true }) as HTMLInputElement).checked).toBe(true);
    expect(change).not.toHaveBeenCalled();
  });
});
