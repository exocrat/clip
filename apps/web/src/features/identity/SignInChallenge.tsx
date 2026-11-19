import { useEffect, useRef } from 'react';
import { createRoot } from 'react-dom/client';

type Widget = {
  render(element: HTMLElement, options: Record<string, unknown>): string;
  remove(id: string): void;
};
declare global { interface Window { turnstile?: Widget } }
let loading: Promise<Widget> | null = null;
let active = false;

/** Load the fixed provider script only after a challenged authentication operation; allow retry on failure. */
function provider(): Promise<Widget> {
  if (window.turnstile) return Promise.resolve(window.turnstile);
  if (!loading) loading = new Promise<Widget>((resolve, reject) => {
    const script = document.createElement('script');
    const timeout = setTimeout(fail, 10_000);
    function fail() {
      clearTimeout(timeout);
      script.remove();
      loading = null;
      reject(new Error('Security check unavailable.'));
    }
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
    script.async = true;
    script.onerror = fail;
    script.onload = () => {
      clearTimeout(timeout);
      if (window.turnstile) resolve(window.turnstile);
      else fail();
    };
    document.head.append(script);
  });
  return loading;
}

/** Accessible modal owns one widget and removes it on completion, cancellation or expiry. */
function Challenge({ siteKey, finish }: {
  siteKey: string; finish: (token?: string) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let disposed = false;
    let widget: string | undefined;
    let api: Widget | undefined;
    dialog.current?.showModal();
    const timeout = setTimeout(() => finish(), 120_000);
    void provider().then((value) => {
      if (disposed || !container.current) return;
      api = value;
      widget = value.render(container.current, {
        sitekey: siteKey, action: 'clip_signin',
        callback: (token: string) => finish(token),
        'error-callback': () => finish(),
        'expired-callback': () => finish(),
        'timeout-callback': () => finish(),
      });
    }).catch(() => finish());
    return () => {
      disposed = true;
      clearTimeout(timeout);
      if (widget !== undefined) api?.remove(widget);
      dialog.current?.close();
    };
  }, [siteKey, finish]);
  return <dialog ref={dialog} aria-labelledby="signin-check-title" onCancel={(event) => {
    event.preventDefault(); finish();
  }}>
    <h2 id="signin-check-title">Complete a security check</h2>
    <p>Sign-in traffic is high. Complete this check to continue your sign-in.</p>
    <div ref={container} />
    <button type="button" onClick={() => finish()}>Cancel</button>
  </dialog>;
}

/** One proof authorizes only the pending rejected operation; never store it or share it. */
export function solveSignInChallenge(siteKey: string, signal?: AbortSignal): Promise<string> {
  if (active || signal?.aborted || !/^[A-Za-z0-9_-]{10,256}$/.test(siteKey))
    return Promise.reject(new Error('Security check unavailable.'));
  active = true;
  return new Promise((resolve, reject) => {
    const previous = document.activeElement;
    const host = document.createElement('div');
    document.body.append(host);
    const root = createRoot(host);
    let settled = false;
    const cancel = () => finish();
    function finish(token?: string) {
      if (settled) return;
      settled = true;
      signal?.removeEventListener('abort', cancel);
      window.removeEventListener('pagehide', cancel);
      window.removeEventListener('popstate', cancel);
      active = false;
      // Completion can arrive during an effect; defer root disposal past that render.
      queueMicrotask(() => {
        root.unmount(); host.remove();
        if (previous instanceof HTMLElement && previous.isConnected) previous.focus();
      });
      if (token && token.length <= 2048) resolve(token);
      else reject(new Error('Security check did not complete. Please try again.'));
    }
    signal?.addEventListener('abort', cancel, { once: true });
    window.addEventListener('pagehide', cancel, { once: true });
    window.addEventListener('popstate', cancel, { once: true });
    root.render(<Challenge siteKey={siteKey} finish={finish} />);
  });
}
