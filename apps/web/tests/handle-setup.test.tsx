// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { IdentityError } from '../src/features/identity/api';
import { HandleEditor, HandleSetup } from '../src/features/identity/HandleSetup';
const state = vi.hoisted(() => ({ user: { user_id: 'actor', display_name: null as string | null, handle_ready: false }, refresh: vi.fn(async () => null), request: vi.fn(async (..._args: unknown[]) => ({})) }));
vi.mock('../src/features/identity/session', () => ({ useIdentity: () => ({ status: 'ready', user: state.user, refresh: state.refresh }) }));
vi.mock('../src/features/identity/api', async (original) => ({ ...await original<typeof import('../src/features/identity/api')>(), request: state.request }));
afterEach(() => { cleanup(); state.request.mockReset(); state.refresh.mockClear(); state.user = { user_id: 'actor', display_name: null, handle_ready: false }; });

describe('required Handle setup', () => {
  it('requires setup until the server confirms a completed claim', () => {
    const { rerender } = render(<HandleSetup><p>Marketplace</p></HandleSetup>);
    expect(screen.queryByText('Marketplace')).toBeNull();
    expect(screen.getByLabelText('Handle')).toBeTruthy();
    state.user.handle_ready = true;
    rerender(<HandleSetup><p>Marketplace</p></HandleSetup>);
    expect(screen.getByText('Marketplace')).toBeTruthy();
  });
  it('sends a trimmed claim and refreshes the authoritative session', async () => {
    state.request.mockResolvedValue({});
    render(<HandleEditor />);
    fireEvent.change(screen.getByLabelText('Handle'), { target: { value: '  Campus_One  ' } });
    const form = screen.getByLabelText('Handle').closest('form');
    if (!form) throw new Error('Missing Handle form');
    fireEvent.submit(form);
    await screen.findByText('Handle saved.');
    expect(state.request).toHaveBeenCalledWith('/me/profile', 'PATCH', { display_name: 'Campus_One' }, true, expect.any(AbortSignal));
    expect(state.refresh).toHaveBeenCalledOnce();
  });
  it('shows a safe taken-name error and preserves the draft', async () => {
    state.request.mockRejectedValue(new IdentityError(409));
    render(<HandleEditor />);
    fireEvent.change(screen.getByLabelText('Handle'), { target: { value: 'Taken_Handle' } });
    const form = screen.getByLabelText('Handle').closest('form');
    if (!form) throw new Error('Missing Handle form');
    fireEvent.submit(form);
    await screen.findByText('That Handle is taken. Choose another.');
    expect((screen.getByLabelText('Handle') as HTMLInputElement).value).toBe('Taken_Handle');
    expect(state.refresh).not.toHaveBeenCalled();
  });
});
