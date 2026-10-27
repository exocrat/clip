import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { useIdentity } from '../identity';
import { Button } from '../../shared/ui';
import { ListingsApiError, startListingConversation } from './listingsApi';

/** Public Listings action: the origin owner authorizes creation before navigation. */
export function StartListingConversationAction({ listingId }: { listingId?: string }) {
  const { status, user } = useIdentity();
  if (status !== 'ready' || !user) return <p role="status">Sign in to message the seller.</p>;
  if (!listingId) return null;
  return <StartAction key={`${user.user_id}:${listingId}`} listingId={listingId} />;
}

/** One actor/origin intent; cancellation prevents late results from navigating. */
function StartAction({ listingId }: { listingId: string }) {
  const navigate = useNavigate();
  const operation = useRef<string | null>(null);
  const request = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => () => { request.current?.abort(); }, []);

  const open = async () => {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError('');
    try {
      operation.current ??= crypto.randomUUID();
      const result = await startListingConversation(listingId, operation.current, controller.signal);
      if (!controller.signal.aborted) navigate(`/my/conversations/${encodeURIComponent(result.conversation_id)}`);
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof ListingsApiError
        ? failure.message : 'Couldn’t open the conversation. Try again.');
    } finally {
      request.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  };
  return <div>
    <Button disabled={busy} onClick={() => { void open(); }}>{busy ? 'Opening conversation…' : 'Message seller'}</Button>
    {error ? <p role="alert">{error}</p> : null}
  </div>;
}
