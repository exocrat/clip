/** Allow synthetic conversation previews only in a development build on loopback. */
export function isLocalConversationDemoAllowed(
  isDevelopmentBuild: boolean,
  hostname: string,
  search: string,
): boolean {
  if (!isDevelopmentBuild || !['localhost', '127.0.0.1', '::1', '[::1]'].includes(hostname)) {
    return false;
  }
  return new URLSearchParams(search).get('demo') === 'conversations';
}
