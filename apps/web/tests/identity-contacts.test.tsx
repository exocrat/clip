// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { SessionView } from '../../../contracts/generated/types.gen';
import { ContactsEditor, IdentityProvider, useIdentity } from '../src/features/identity';
import { identityApi } from '../src/features/identity/api';

const actor: SessionView = {
  user_id: '11111111-2222-4333-8444-555555555555',
  account_class: 'temporary',
  valid_until: '2100-01-01T00:00:00.000000Z',
};
const other: SessionView = { ...actor, user_id: 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee' };
const values = {
  email: 'synthetic-source@example.com',
  phone: '+919876543210',
  upi_id: 'synthetic@oktest',
};
const blank = { email: null, phone: null, upi_id: null };
function response(body: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(body), { status });
}
function mock(handler: (path: string, init: RequestInit) => Response | Promise<Response>) {
  const fetcher = vi.fn((path: string, init: RequestInit) => Promise.resolve(handler(path, init)));
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}
function Controls() {
  const identity = useIdentity();
  return (
    <>
      <button type="button" onClick={identity.clear}>
        Fixture logout
      </button>
      <button type="button" onClick={() => identity.accept(other)}>
        Fixture account switch
      </button>
    </>
  );
}
function view() {
  return render(
    <MemoryRouter initialEntries={['/account/contacts?user_id=forged']}>
      <IdentityProvider>
        <Controls />
        <ContactsEditor />
      </IdentityProvider>
    </MemoryRouter>,
  );
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('Private own-contact editor', () => {
  it('does not fetch contact values for an anonymous caller or browser-supplied actor', async () => {
    const fetcher = mock(() => response({}, 401));
    view();
    await screen.findByRole('heading', { name: 'Sign in to edit your contact details' });
    expect(fetcher.mock.calls.map((row) => row[0])).toEqual(['/me']);
    expect(screen.queryByLabelText('Contact email')).toBeNull();
  });

  it.each(['regular', 'temporary'] as const)(
    'supports empty own contacts for %s without inventing values',
    async (account_class) => {
      mock((path) => (path === '/me' ? response({ ...actor, account_class }) : response(blank)));
      view();
      expect((await screen.findByLabelText('Contact email')).getAttribute('value')).toBe('');
      expect(screen.getByText('No saved email.')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Delete email' }).hasAttribute('disabled')).toBe(
        true,
      );
      expect(screen.getByRole('button', { name: 'Save email' }).hasAttribute('disabled')).toBe(
        true,
      );
    },
  );

  it('saves one field with CSRF then refetches, preserving unrelated values', async () => {
    let saved = { ...values };
    const calls: { path: string; init: RequestInit }[] = [];
    mock((path, init) => {
      calls.push({ path, init });
      if (path === '/me') return response(actor);
      if (path === '/auth/csrf') return response({ csrf_token: 'synthetic-contact-csrf' });
      if (init.method === 'PUT') {
        saved = { ...saved, email: JSON.parse(String(init.body)).value };
        return response(null, 204);
      }
      return response(saved);
    });
    const user = userEvent.setup();
    view();
    await screen.findByDisplayValue(values.email);
    await user.clear(screen.getByLabelText('Contact email'));
    await user.type(screen.getByLabelText('Contact email'), 'new-synthetic@example.com');
    await user.click(screen.getByRole('button', { name: 'Save email' }));
    await screen.findByDisplayValue('new-synthetic@example.com');
    expect(screen.getByLabelText('Phone number').getAttribute('value')).toBe(values.phone);
    expect(screen.getByLabelText('UPI ID').getAttribute('value')).toBe(values.upi_id);
    expect(screen.getByRole('status').textContent).toBe('Email saved.');
    const write = calls.find((row) => row.init.method === 'PUT');
    expect(write?.path).toBe('/me/contacts/email');
    expect(write?.init.headers).toEqual({
      'X-CLIP-Request': '1',
      'Content-Type': 'application/json',
      'X-CSRF-Token': 'synthetic-contact-csrf',
    });
    expect(JSON.parse(String(write?.init.body))).toEqual({ value: 'new-synthetic@example.com' });
    expect(calls.filter((row) => row.path === '/me/contacts')).toHaveLength(2);
  });

  it('hides a confirmed deleted value while its authoritative refetch is pending', async () => {
    let reads = 0;
    let finish: ((result: Response) => void) | undefined;
    mock((path, init) => {
      if (path === '/me') return response(actor);
      if (path === '/auth/csrf') return response({ csrf_token: 'synthetic-contact-csrf' });
      if (init.method === 'DELETE') return response(null, 204);
      reads++;
      return reads === 1
        ? response(values)
        : new Promise<Response>((resolve) => {
            finish = resolve;
          });
    });
    const user = userEvent.setup();
    view();
    await screen.findByDisplayValue(values.email);
    await user.click(screen.getByRole('button', { name: 'Delete email' }));
    await screen.findByText('Email deleted.');
    expect(screen.queryByDisplayValue(values.email)).toBeNull();
    await act(async () => {
      finish?.(response({ ...values, email: null }));
    });
    await screen.findByText('No saved email.');
    expect(screen.getByLabelText('Contact email').getAttribute('value')).toBe('');
    expect(screen.getByLabelText('Phone number').getAttribute('value')).toBe(values.phone);
  });

  it('shows field validation errors without private dependency payload or OTP guidance', async () => {
    mock((path, init) =>
      path === '/me'
        ? response(actor)
        : path === '/auth/csrf'
          ? response({ csrf_token: 'synthetic-contact-csrf' })
          : init.method === 'PUT'
            ? response({ error: { message: 'PRIVATE_CONTACT_DETAIL' } }, 422)
            : response(values),
    );
    const user = userEvent.setup();
    view();
    await screen.findByDisplayValue(values.upi_id);
    await user.clear(screen.getByLabelText('UPI ID'));
    await user.type(screen.getByLabelText('UPI ID'), 'invalid');
    await user.click(screen.getByRole('button', { name: 'Save upi id' }));
    expect((await screen.findByRole('alert')).textContent).toBe(
      'Check the contact format and try again.',
    );
    expect(document.body.textContent).not.toContain('PRIVATE_CONTACT_DETAIL');
    expect(screen.getByLabelText('UPI ID').getAttribute('value')).toBe('invalid');
  });

  it('does not treat an outage as empty contacts, and permits an explicit safe retry', async () => {
    let down = true;
    mock((path) => (path === '/me' ? response(actor) : down ? response({}, 503) : response(blank)));
    const user = userEvent.setup();
    view();
    await screen.findByRole('alert');
    expect(screen.queryByLabelText('Contact email')).toBeNull();
    expect(screen.queryByText('No saved email.')).toBeNull();
    down = false;
    await user.click(screen.getByRole('button', { name: 'Refresh contacts' }));
    await screen.findByText('No saved email.');
  });

  it('clears private values and stale responses on logout', async () => {
    let finish: ((result: Response) => void) | undefined;
    mock((path) =>
      path === '/me'
        ? response(actor)
        : new Promise<Response>((resolve) => {
            finish = resolve;
          }),
    );
    const user = userEvent.setup();
    view();
    await screen.findByText('Loading your contact details…');
    await user.click(screen.getByRole('button', { name: 'Fixture logout' }));
    await act(async () => {
      finish?.(response(values));
    });
    await screen.findByRole('heading', { name: 'Sign in to edit your contact details' });
    expect(screen.queryByDisplayValue(values.email)).toBeNull();
  });

  it('ignores old account reads after a trusted session-context switch', async () => {
    let reads = 0;
    let finish: ((result: Response) => void) | undefined;
    mock((path) => {
      if (path === '/me') return response(actor);
      reads++;
      return reads === 1
        ? new Promise<Response>((resolve) => {
            finish = resolve;
          })
        : response({ ...blank, email: 'other-synthetic@example.com' });
    });
    const user = userEvent.setup();
    view();
    await screen.findByText('Loading your contact details…');
    await user.click(screen.getByRole('button', { name: 'Fixture account switch' }));
    await screen.findByDisplayValue('other-synthetic@example.com');
    await act(async () => {
      finish?.(response(values));
    });
    expect(screen.queryByDisplayValue(values.email)).toBeNull();
    expect(screen.getByLabelText('Contact email').getAttribute('value')).toBe(
      'other-synthetic@example.com',
    );
  });

  it('ignores a late write/refetch from an unmounted account editor', async () => {
    let reads = 0;
    let finish: ((result: Response) => void) | undefined;
    mock((path, init) => {
      if (path === '/me') return response(actor);
      if (path === '/auth/csrf') return response({ csrf_token: 'synthetic-contact-csrf' });
      if (init.method === 'PUT')
        return new Promise<Response>((resolve) => {
          finish = resolve;
        });
      reads++;
      return response(reads === 1 ? values : { ...blank, email: 'other-synthetic@example.com' });
    });
    const user = userEvent.setup();
    view();
    await screen.findByDisplayValue(values.email);
    await user.clear(screen.getByLabelText('Contact email'));
    await user.type(screen.getByLabelText('Contact email'), 'pending-synthetic@example.com');
    await user.click(screen.getByRole('button', { name: 'Save email' }));
    await waitFor(() => expect(finish).toBeDefined());
    await user.click(screen.getByRole('button', { name: 'Fixture account switch' }));
    await screen.findByDisplayValue('other-synthetic@example.com');
    await act(async () => {
      finish?.(response(null, 204));
    });
    expect(reads).toBe(2);
    expect(screen.getByLabelText('Contact email').getAttribute('value')).toBe(
      'other-synthetic@example.com',
    );
  });

  it('hides ambiguous results and never automatically retries a contact write', async () => {
    let writes = 0;
    let reads = 0;
    mock((path, init) => {
      if (path === '/me') return response(actor);
      if (path === '/auth/csrf') return response({ csrf_token: 'synthetic-contact-csrf' });
      if (init.method === 'PUT') {
        writes++;
        throw new Error('PRIVATE_CONTACT_DEPENDENCY');
      }
      reads++;
      return response(values);
    });
    const user = userEvent.setup();
    view();
    await screen.findByDisplayValue(values.email);
    await user.clear(screen.getByLabelText('Contact email'));
    await user.type(screen.getByLabelText('Contact email'), 'uncertain-synthetic@example.com');
    await user.click(screen.getByRole('button', { name: 'Save email' }));
    expect((await screen.findByRole('alert')).textContent).toMatch(/Refresh your contacts/);
    expect(screen.queryByLabelText('Contact email')).toBeNull();
    expect(document.body.textContent).not.toContain('PRIVATE_CONTACT_DEPENDENCY');
    expect(writes).toBe(1);
    expect(reads).toBe(1);
    await user.click(screen.getByRole('button', { name: 'Refresh contacts' }));
    await screen.findByDisplayValue(values.email);
    expect(writes).toBe(1);
  });

  it('hides contacts immediately after a fresh unauthorized response', async () => {
    let denied = false;
    mock((path) =>
      denied ? response({}, 401) : path === '/me' ? response(actor) : response(values),
    );
    const user = userEvent.setup();
    view();
    await screen.findByDisplayValue(values.email);
    denied = true;
    await user.click(screen.getByRole('button', { name: 'Refresh contacts' }));
    await screen.findByRole('heading', { name: 'Sign in to edit your contact details' });
    expect(screen.queryByDisplayValue(values.email)).toBeNull();
  });

  it('ignores duplicate contact submissions while a write is pending', async () => {
    let writes = 0;
    let finish: ((result: Response) => void) | undefined;
    mock((path, init) => {
      if (path === '/me') return response(actor);
      if (path === '/auth/csrf') return response({ csrf_token: 'synthetic-contact-csrf' });
      if (init.method === 'PUT') {
        writes++;
        return new Promise<Response>((resolve) => {
          finish = resolve;
        });
      }
      return response(values);
    });
    view();
    await screen.findByDisplayValue(values.email);
    fireEvent.change(screen.getByLabelText('Contact email'), {
      target: { value: 'duplicate-synthetic@example.com' },
    });
    const form = screen.getByRole('form', { name: 'Email contact' });
    fireEvent.submit(form);
    fireEvent.submit(form);
    await waitFor(() => expect(writes).toBe(1));
    await act(async () => {
      finish?.(response(null, 204));
    });
    await screen.findByDisplayValue(values.email);
    expect(writes).toBe(1);
  });
});

describe('Own-contact response boundary', () => {
  it('strips extra fields and never sends an actor ID', async () => {
    const fetcher = mock(() => response({ ...values, secret: 'PRIVATE_EXTRA' }));
    expect(await identityApi.contacts()).toEqual(values);
    expect(fetcher.mock.calls[0][0]).toBe('/me/contacts');
  });
  it.each([{ email: null }, { ...values, phone: 123 }, null])(
    'rejects malformed contact dependencies',
    async (result) => {
      mock(() => response(result));
      await expect(identityApi.contacts()).rejects.toMatchObject({ status: 503 });
    },
  );
});

describe('Private draft lifecycle', () => {
  it('preserves an unfinished own draft on ordinary focus without browser persistence', async () => {
    const storage = vi.spyOn(Storage.prototype, 'setItem');
    const fetcher = mock((path) => (path === '/me' ? response(actor) : response(values)));
    const user = userEvent.setup();
    view();
    await screen.findByDisplayValue(values.email);
    await user.clear(screen.getByLabelText('Contact email'));
    await user.type(screen.getByLabelText('Contact email'), 'unfinished-synthetic@example.com');
    fireEvent.focus(window);
    await waitFor(() =>
      expect(fetcher.mock.calls.filter((row) => row[0] === '/me')).toHaveLength(2),
    );
    expect(screen.getByLabelText('Contact email').getAttribute('value')).toBe(
      'unfinished-synthetic@example.com',
    );
    expect(fetcher.mock.calls.filter((row) => row[0] === '/me/contacts')).toHaveLength(1);
    expect(storage).not.toHaveBeenCalled();
  });

  it.each([403, 503])('hides private rows after a definite write failure %s', async (status) => {
    mock((path, init) =>
      path === '/me'
        ? response(actor)
        : path === '/auth/csrf'
          ? response({ csrf_token: 'synthetic-contact-csrf' })
          : init.method === 'PUT'
            ? response({ detail: 'PRIVATE_FAILURE' }, status)
            : response(values),
    );
    const user = userEvent.setup();
    view();
    await screen.findByDisplayValue(values.email);
    await user.clear(screen.getByLabelText('Contact email'));
    await user.type(screen.getByLabelText('Contact email'), 'failed-synthetic@example.com');
    await user.click(screen.getByRole('button', { name: 'Save email' }));
    await screen.findByRole('alert');
    expect(screen.queryByLabelText('Contact email')).toBeNull();
    expect(document.body.textContent).not.toContain('PRIVATE_FAILURE');
    expect(screen.queryByText('Email saved.')).toBeNull();
  });
});

describe('Independent contact drafts', () => {
  it('preserves another field’s unsaved draft when refetching a confirmed save', async () => {
    let saved = { ...values };
    mock((path, init) => {
      if (path === '/me') return response(actor);
      if (path === '/auth/csrf') return response({ csrf_token: 'synthetic-contact-csrf' });
      if (init.method === 'PUT') {
        saved = { ...saved, email: JSON.parse(String(init.body)).value };
        return response(null, 204);
      }
      return response(saved);
    });
    const user = userEvent.setup();
    view();
    await screen.findByDisplayValue(values.email);
    await user.clear(screen.getByLabelText('Phone number'));
    await user.type(screen.getByLabelText('Phone number'), '+919999999999');
    await user.clear(screen.getByLabelText('Contact email'));
    await user.type(screen.getByLabelText('Contact email'), 'independent-synthetic@example.com');
    await user.click(screen.getByRole('button', { name: 'Save email' }));
    await screen.findByDisplayValue('independent-synthetic@example.com');
    expect(screen.getByLabelText('Phone number').getAttribute('value')).toBe('+919999999999');
    expect(saved.phone).toBe(values.phone);
  });
});
