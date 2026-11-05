/** Retain only a hash of the server's opaque request ID, never other headers.
 * The application overwrites client IDs. Missing IDs on rejected/transport
 * requests remain unattributed; they must not be invented or called cold starts.
 */
export function responseCorrelation(response, hashId) {
  const headers = response && response.headers;
  if (!headers || typeof headers !== 'object') return { correlation: 'unattributed' };
  const names = Object.keys(headers).filter(name => name.toLowerCase() === 'x-request-id');
  if (names.length !== 1) return { correlation: 'unattributed' };
  const value = headers[names[0]];
  if (typeof value !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value)) {
    return { correlation: 'invalid_server_id' };
  }
  const digest = hashId(value);
  if (typeof digest !== 'string' || !/^[0-9a-f]{64}$/.test(digest)) throw Error('invalid_correlation_hash');
  return { correlation: 'server_id', request_id_sha256: digest };
}
