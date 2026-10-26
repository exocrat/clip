import { useState } from 'react';
import { Button } from '../../shared/ui';

/** Development-only synthetic inbox. Vite removes this module from normal builds.
 * Only the explicit loopback preview harness exposes the fixed test mailbox.
 */
export default function PreviewMailbox() {
  const [code, setCode] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  async function check() {
    setBusy(true);
    setError(false);
    try {
      const response = await fetch('/__identity_preview__/mail', {
        credentials: 'same-origin',
        cache: 'no-store',
      });
      if (!response.ok) throw new Error();
      const result: unknown = await response.json();
      const value = result && typeof result === 'object' && 'code' in result ? result.code : null;
      setCode(typeof value === 'string' && /^[0-9]{6}$/.test(value) ? value : null);
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className="identity-preview" aria-label="Synthetic test inbox">
      <p>
        For this local test, use <strong>preview@example.invalid</strong>. Use a made-up password.
        The test inbox replaces email delivery.
      </p>
      <Button
        variant="secondary"
        disabled={busy}
        onClick={() => {
          void check();
        }}
      >
        {busy ? 'Checking test inbox…' : 'Check test inbox'}
      </Button>
      {code && (
        <p role="status">
          Synthetic verification code: <strong>{code}</strong>
        </p>
      )}
      {error && <p role="alert">Test inbox is unavailable.</p>}
    </aside>
  );
}
