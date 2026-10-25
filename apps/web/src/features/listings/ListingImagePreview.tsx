import { useEffect, useState } from 'react';
import { Button } from '../../shared/ui';
import { readImageDelivery } from './listingsApi';
import { ListingPhotoPlaceholder } from './ListingPhotoPlaceholder';
import './listings.css';

/** Resolve an authorized short-lived image link and recover when it expires. */
export function ListingImagePreview({
  imageId,
  alt,
  compact = false,
  allowRetry = true,
}: {
  imageId: string;
  alt: string;
  compact?: boolean;
  allowRetry?: boolean;
}) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setUrl('');
    setError(false);
    readImageDelivery(imageId, controller.signal).then((delivery) => {
      if (!controller.signal.aborted) setUrl(delivery.url);
    }).catch(() => {
      if (!controller.signal.aborted) setError(true);
    });
    return () => controller.abort();
  }, [imageId, retry]);

  if (error) {
    return (
      <div className="listings-image-unavailable">
        <ListingPhotoPlaceholder compact={compact} message="Temporarily unavailable" />
        <p className="listings-muted">This photo couldn’t be loaded.</p>
        {allowRetry ? (
          <Button variant="secondary" onClick={() => setRetry((current) => current + 1)}>
            Retry photo
          </Button>
        ) : null}
      </div>
    );
  }
  if (!url) {
    return <div className="listings-image-loading" role="status">Loading photo…</div>;
  }
  return (
    <img
      className={`listings-image-preview${compact ? ' listings-image-preview--compact' : ''}`}
      src={url}
      alt={alt}
      onError={() => setError(true)}
    />
  );
}
