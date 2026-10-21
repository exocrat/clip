import { useState } from 'react';
import { ListingPhotoPlaceholder } from './ListingPhotoPlaceholder';

/** Show one selected photo area and a thumbnail choice for each remaining photo. */
export function ListingPhotoGallery({ imageIds }: { imageIds: string[] }) {
  const [selected, setSelected] = useState(0);
  const safeIndex = imageIds.length ? Math.min(selected, imageIds.length - 1) : 0;
  const others = imageIds.map((id, index) => ({ id, index })).filter(({ index }) => index !== safeIndex);

  return (
    <div className="listings-gallery">
      <figure className="listings-photo listings-gallery__main">
        <ListingPhotoPlaceholder />
        <figcaption className="listings-muted">
          {imageIds.length ? `Photo ${safeIndex + 1} of ${imageIds.length}. Real photo delivery is not connected yet.` : 'No photos are attached to this listing.'}
        </figcaption>
      </figure>
      {others.length ? (
        <fieldset className="listings-gallery__thumbnails">
          <legend>Other listing photos</legend>
          {others.map(({ id, index }) => (
            <button
              className="listings-gallery__thumbnail"
              key={id}
              type="button"
              aria-label={`Show photo ${index + 1}`}
              onClick={() => setSelected(index)}
            >
              <ListingPhotoPlaceholder compact />
              <span>Photo {index + 1}</span>
            </button>
          ))}
        </fieldset>
      ) : null}
    </div>
  );
}
