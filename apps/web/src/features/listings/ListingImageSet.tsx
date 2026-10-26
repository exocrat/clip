import { useEffect, useRef, useState, type ChangeEvent } from 'react';
import { Button } from '../../shared/ui';
import type { ExistingListingImage, NewListingImage } from '../../../../../contracts/generated/types.gen';
import { cancelImageUpload, ListingImageFinalError, uploadListingImage } from './listingsApi';
import { ListingImagePreview } from './ListingImagePreview';
import { ListingPhotoPlaceholder } from './ListingPhotoPlaceholder';
import { newOperationId } from './operationId';

export type ListingImageChoice = ExistingListingImage | NewListingImage;

const allowedTypes = new Set(['image/jpeg', 'image/png', 'image/webp']);
const maximumBytes = 10 * 1024 * 1024;

type PendingPhoto = {
  localId: string;
  file: File;
  previewUrl: string;
  operationId: string;
  uploadId?: string;
  progress: number;
  phase: 'queued' | 'uploading' | 'confirming' | 'failed';
  error?: string;
  retryable?: boolean;
};

/** A corrupt local file must show a usable fallback while the server checks it. */
function SelectedPreview({ url, alt }: { url: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  return failed
    ? <ListingPhotoPlaceholder compact message="Preview unavailable" />
    : <img className="listings-image-preview listings-image-preview--compact" src={url} alt={alt} onError={() => setFailed(true)} />;
}

/** Upload selected photos, show progress, and preserve their order for the listing form. */
export function ListingImageSet({
  images,
  onChange,
  onBusyChange,
  onPendingChange,
  disabled = false,
  error,
}: {
  images: ListingImageChoice[];
  onChange: (images: ListingImageChoice[]) => void;
  onBusyChange?: (busy: boolean) => void;
  onPendingChange?: (pending: boolean) => void;
  disabled?: boolean;
  error?: string;
}) {
  const galleryInput = useRef<HTMLInputElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);
  const previewUrls = useRef(new Map<string, string>());
  const imagesRef = useRef(images);
  const mounted = useRef(true);
  const running = useRef(false);
  const transfer = useRef<AbortController | null>(null);
  imagesRef.current = images;
  const [pending, setPending] = useState<PendingPhoto[]>([]);
  const [rejections, setRejections] = useState<string[]>([]);
  const [notice, setNotice] = useState('');
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    onBusyChange?.(uploading);
  }, [onBusyChange, uploading]);

  useEffect(() => {
    onPendingChange?.(pending.length > 0);
  }, [onPendingChange, pending.length]);

  // File inputs dispatch a native cancel event; React's input props do not
  // include it. Cancellation never changes the already-selected photos.
  useEffect(() => {
    const inputs = [galleryInput.current, cameraInput.current];
    const cancelled = () => setNotice('No photo was selected. Your current photos are unchanged.');
    for (const input of inputs) input?.addEventListener('cancel', cancelled);
    return () => {
      for (const input of inputs) input?.removeEventListener('cancel', cancelled);
    };
  }, []);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      transfer.current?.abort();
      for (const url of previewUrls.current.values()) URL.revokeObjectURL(url);
      previewUrls.current.clear();
    };
  }, []);

  const occupiedSlots = images.length + pending.length;
  const controlsDisabled = disabled || uploading || occupiedSlots >= 8;

  function updatePending(localId: string, update: (item: PendingPhoto) => PendingPhoto) {
    if (!mounted.current) return;
    setPending((current) => current.map((item) => item.localId === localId ? update(item) : item));
  }

  async function upload(item: PendingPhoto, signal: AbortSignal) {
    updatePending(item.localId, (current) => ({ ...current, phase: 'uploading', error: undefined }));
    try {
      const confirmed = await uploadListingImage(
        item.file,
        item.operationId,
        (progress) => updatePending(item.localId, (current) => ({
          ...current,
          progress,
          phase: progress >= 100 ? 'confirming' : 'uploading',
        })),
        (uploadId) => updatePending(item.localId, (current) => ({ ...current, uploadId })),
        item.uploadId,
        signal,
      );
      if (!mounted.current) {
        URL.revokeObjectURL(item.previewUrl);
        try { await cancelImageUpload(confirmed.upload_id); } catch { /* Expiry cleanup remains safe. */ }
        return;
      }
      previewUrls.current.set(confirmed.upload_id, item.previewUrl);
      previewUrls.current.delete(item.localId);
      const next = [...imagesRef.current, { source: 'upload' as const, upload_id: confirmed.upload_id }];
      imagesRef.current = next;
      onChange(next);
      setPending((current) => current.filter((photo) => photo.localId !== item.localId));
    } catch (failure) {
      if (!mounted.current) return;
      updatePending(item.localId, (current) => ({
        ...current,
        phase: 'failed',
        error: (failure as Error).message,
        retryable: !(failure instanceof ListingImageFinalError),
      }));
    }
  }

  async function runUploads(items: PendingPhoto[]) {
    // Reserve the queue synchronously, before React updates disabled buttons.
    // Keep it busy across the whole batch, including time between files.
    if (running.current || disabled || !mounted.current) return;
    running.current = true;
    setUploading(true);
    const controller = new AbortController();
    transfer.current = controller;
    try {
      for (const item of items) {
        if (!mounted.current || controller.signal.aborted) break;
        await upload(item, controller.signal);
      }
    } finally {
      running.current = false;
      transfer.current = null;
      if (mounted.current) setUploading(false);
    }
  }

  function chooseFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = [...(event.currentTarget.files ?? [])];
    event.currentTarget.value = '';
    if (!files.length || running.current || disabled) return;

    setNotice('');
    const messages: string[] = [];
    const accepted: PendingPhoto[] = [];
    let remaining = Math.max(0, 8 - occupiedSlots);
    for (const file of files) {
      if (remaining <= 0) {
        messages.push(`${file.name || 'This photo'} was not added. A listing can have up to 8 photos.`);
        continue;
      }
      if (!allowedTypes.has(file.type)) {
        messages.push(`${file.name || 'This photo'} was not added. Choose a JPEG, PNG, or WebP photo.`);
        continue;
      }
      if (file.size < 1 || file.size > maximumBytes) {
        messages.push(`${file.name || 'This photo'} was not added. Each photo must be 10 MiB or smaller and not empty.`);
        continue;
      }
      try {
        const localId = newOperationId();
        const previewUrl = URL.createObjectURL(file);
        previewUrls.current.set(localId, previewUrl);
        accepted.push({
          localId,
          file,
          previewUrl,
          operationId: localId,
          progress: 0,
          phase: 'queued',
          retryable: true,
        });
        remaining -= 1;
      } catch {
        messages.push(`${file.name || 'This photo'} could not be previewed. Try choosing it again.`);
      }
    }
    setRejections(messages);
    if (accepted.length) {
      setPending((current) => [...current, ...accepted]);
      void runUploads(accepted);
    }
  }

  async function removePending(item: PendingPhoto) {
    setPending((current) => current.filter((photo) => photo.localId !== item.localId));
    URL.revokeObjectURL(item.previewUrl);
    previewUrls.current.delete(item.localId);
    if (item.uploadId) {
      try { await cancelImageUpload(item.uploadId); } catch { /* Expiry cleanup remains safe. */ }
    }
  }

  function removeImage(index: number) {
    const [removed] = images.slice(index, index + 1);
    const next = images.filter((_, imageIndex) => imageIndex !== index);
    imagesRef.current = next;
    onChange(next);
    if (removed?.source === 'upload') {
      const preview = previewUrls.current.get(removed.upload_id);
      if (preview) URL.revokeObjectURL(preview);
      previewUrls.current.delete(removed.upload_id);
      void cancelImageUpload(removed.upload_id).catch(() => undefined);
    }
  }

  function move(index: number, offset: -1 | 1) {
    const target = index + offset;
    if (target < 0 || target >= images.length) return;
    const next = [...images];
    [next[index], next[target]] = [next[target], next[index]];
    imagesRef.current = next;
    onChange(next);
  }

  return (
    <fieldset id="listing-images" disabled={disabled} className="listings-image-picker">
      <legend>Listing photos</legend>
      <p>Choose 1–8 photos. JPEG, PNG, or WebP; each photo must be 10 MiB or smaller.</p>
      <p role="status">{images.length} confirmed photo{images.length === 1 ? '' : 's'} selected · {occupiedSlots} of 8 slots in use</p>
      <input
        ref={galleryInput}
        className="listings-file-input"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        disabled={controlsDisabled}
        tabIndex={-1}
        onChange={chooseFiles}
        aria-label="Choose photos from your files or gallery"
      />
      <input
        ref={cameraInput}
        className="listings-file-input"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        disabled={controlsDisabled}
        tabIndex={-1}
        onChange={chooseFiles}
        aria-label="Take a photo using your device camera"
      />
      <div className="listings-image-picker__controls">
        <Button variant="secondary" disabled={controlsDisabled} onClick={() => galleryInput.current?.click()}>
          Choose photos
        </Button>
        <Button variant="secondary" disabled={controlsDisabled} onClick={() => cameraInput.current?.click()}>
          Take a photo (supported phones)
        </Button>
      </div>
      <p className="listings-muted">If your browser cannot open the camera, choose a photo from your gallery instead.</p>
      {notice ? <p role="status" className="listings-muted">{notice}</p> : null}
      {rejections.length ? (
        <div role="alert" className="listings-alert">
          <strong>Some photos weren’t added:</strong>
          <ul>{rejections.map((message, index) => <li key={`${index}:${message}`}>{message}</li>)}</ul>
        </div>
      ) : null}
      {error ? <p role="alert" className="listings-error">{error}</p> : null}
      <ol className="listings-image-set">
        {images.map((image, index) => {
          const key = `${image.source}:${image.source === 'existing' ? image.image_id : image.upload_id}`;
          const localUrl = image.source === 'upload' ? previewUrls.current.get(image.upload_id) : undefined;
          return (
            <li className="listings-image-tile" key={key}>
              <div className="listings-image-tile__preview">
                {image.source === 'existing'
                  ? <ListingImagePreview imageId={image.image_id} alt={`Listing item, view ${index + 1}`} compact />
                  : localUrl
                    ? <SelectedPreview url={localUrl} alt={`Listing item, view ${index + 1}`} />
                    : <ListingPhotoPlaceholder compact />}
              </div>
              <strong>Photo {index + 1}</strong>
              <span className="listings-muted">{image.source === 'existing' ? 'Current photo' : 'Uploaded and checked'}</span>
              <div className="listings-image-tile__actions">
                <Button variant="secondary" disabled={disabled || uploading || index === 0} onClick={() => move(index, -1)} aria-label={`Move photo ${index + 1} earlier`}>Move up</Button>
                <Button variant="secondary" disabled={disabled || uploading || index === images.length - 1} onClick={() => move(index, 1)} aria-label={`Move photo ${index + 1} later`}>Move down</Button>
                <Button variant="secondary" disabled={disabled || uploading || images.length <= 1} onClick={() => removeImage(index)} aria-label={`Remove photo ${index + 1}`}>Remove</Button>
              </div>
            </li>
          );
        })}
        {pending.map((item) => (
          <li className="listings-image-tile" key={item.localId}>
            <div className="listings-image-tile__preview">
              <SelectedPreview url={item.previewUrl} alt="Selected item preview" />
            </div>
            <strong>{item.file.name || 'Selected photo'}</strong>
            {item.phase === 'failed' ? (
              <>
                <p role="alert" className="listings-error">{item.error}</p>
                <div className="listings-image-tile__actions">
                  {item.retryable
                    ? <Button variant="secondary" disabled={uploading || disabled} onClick={() => void runUploads([item])}>Retry photo</Button>
                    : null}
                  <Button variant="secondary" disabled={uploading || disabled} onClick={() => void removePending(item)}>Remove photo</Button>
                </div>
              </>
            ) : (
              <>
                <span className="listings-muted">{item.phase === 'confirming' ? 'Checking photo…' : item.phase === 'queued' ? 'Waiting to upload…' : 'Uploading photo…'}</span>
                <progress max="100" value={item.progress} aria-label={`Upload progress for ${item.file.name || 'selected photo'}`} />
              </>
            )}
          </li>
        ))}
      </ol>
      {images.length === 0 && pending.length === 0
        ? <p className="listings-muted">Add at least one photo before publishing this listing.</p>
        : null}
    </fieldset>
  );
}
