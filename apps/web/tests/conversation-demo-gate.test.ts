import { describe, expect, it } from 'vitest';
import { isLocalConversationDemoAllowed } from '../src/pages/conversationDemoGate';

describe('local conversation demo gate', () => {
  it.each(['localhost', '127.0.0.1', '::1', '[::1]'])(
    'allows an explicitly requested development demo on loopback host %s',
    (hostname) => {
      expect(isLocalConversationDemoAllowed(true, hostname, '?demo=conversations')).toBe(true);
    },
  );

  it('does not allow the demo in a production build', () => {
    expect(isLocalConversationDemoAllowed(false, 'localhost', '?demo=conversations')).toBe(false);
  });

  it('does not allow the demo on a non-loopback host, even in development', () => {
    expect(isLocalConversationDemoAllowed(true, 'clip.example.test', '?demo=conversations')).toBe(
      false,
    );
  });

  it('does not activate without the exact explicit query option', () => {
    expect(isLocalConversationDemoAllowed(true, 'localhost', '')).toBe(false);
    expect(isLocalConversationDemoAllowed(true, 'localhost', '?demo=other')).toBe(false);
  });
});
