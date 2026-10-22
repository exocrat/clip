/** A neutral photo area used until the listing has a deliverable image. */
export function ListingPhotoPlaceholder({ compact = false, message = 'Not uploaded yet' }: { compact?: boolean; message?: string }) {
  return (
    <div className={`listings-photo-placeholder${compact ? ' listings-photo-placeholder--compact' : ''}`}>
      <svg viewBox="0 0 80 60" aria-hidden="true" focusable="false">
        <rect x="2" y="2" width="76" height="56" rx="6" />
        <circle cx="56" cy="18" r="6" />
        <path d="M4 46 24 25 44 46 56 34 76 54" />
      </svg>
      <strong>Listing photo</strong>
      <span>{message}</span>
    </div>
  );
}
