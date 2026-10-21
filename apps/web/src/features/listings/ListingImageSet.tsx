import { Button } from '../../shared/ui';
import type { ExistingListingImage, NewListingImage } from '../../../../../contracts/generated/types.gen';
import { ListingPhotoPlaceholder } from './ListingPhotoPlaceholder';

export type ListingImageChoice = ExistingListingImage | NewListingImage;

/** Edit the ordered 1–8 image references while keeping the last one protected. */
export function ListingImageSet({
  images,
  onChange,
  onAddPrepared,
  adding = false,
  disabled = false,
  error,
}: {
  images: ListingImageChoice[];
  onChange: (images: ListingImageChoice[]) => void;
  onAddPrepared?: () => void;
  adding?: boolean;
  disabled?: boolean;
  error?: string;
}) {
  function move(index: number, offset: -1 | 1) {
    const target = index + offset;
    if (target < 0 || target >= images.length) return;
    const next = [...images];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  }

  return (
    <fieldset id="listing-images" disabled={disabled || adding}>
      <legend>Listing photos</legend>
      <p>Keep at least 1 photo and choose its order. You can add up to 8.</p>
      <p role="status">{images.length} of 8 photos selected</p>
      <ol className="listings-image-set">
        {images.map((image, index) => (
          <li className="listings-image-tile" key={`${image.source}:${image.source === 'existing' ? image.image_id : image.upload_id}`}>
            <div className="listings-image-tile__preview"><ListingPhotoPlaceholder compact /></div>
            <strong>Photo {index + 1}</strong>
            <span className="listings-muted">
              {image.source === 'existing' ? 'Current photo' : 'Prepared test record; no photo uploaded'}
            </span>
            <div className="listings-image-tile__actions">
              <Button variant="secondary" disabled={index === 0} onClick={() => move(index, -1)} aria-label={`Move photo ${index + 1} earlier`}>Move up</Button>
              <Button variant="secondary" disabled={index === images.length - 1} onClick={() => move(index, 1)} aria-label={`Move photo ${index + 1} later`}>Move down</Button>
              <Button variant="secondary" disabled={images.length <= 1} onClick={() => onChange(images.filter((_, imageIndex) => imageIndex !== index))} aria-label={`Remove photo ${index + 1}`}>Remove</Button>
            </div>
          </li>
        ))}
      </ol>
      {onAddPrepared && images.length < 8 ? (
        <Button variant="secondary" disabled={adding} onClick={onAddPrepared}>
          {adding ? 'Preparing image record…' : 'Add prepared test image'}
        </Button>
      ) : null}
      {error ? <p role="alert" className="listings-error">{error}</p> : null}
    </fieldset>
  );
}
