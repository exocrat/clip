import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { Button } from '../../shared/ui';
import { ListingNotice } from './ListingNotice';
import { ListingImageSet, type ListingImageChoice } from './ListingImageSet';
import {
  listingPrice,
  readCatalogue,
  readOwnedListing,
  replaceListing,
  type CatalogueView,
  type ListingManagementView,
} from './listingsApi';
import {
  validateListingFields,
  type ListingFormErrors,
  type ListingFormValues,
} from './listingForm';
import './listings.css';

function localDateTime(instant: string): string {
  const date = new Date(instant);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString().slice(0, 16);
}

function listingValues(listing: ListingManagementView): ListingFormValues {
  return {
    title: listing.title,
    description: listing.description,
    category_code: listing.category_code,
    condition_code: listing.condition_code,
    price_rupees: String(listing.asking_price_paise / 100),
    negotiable: listing.negotiable,
    pickup_area: listing.pickup_area ?? '',
    available_from: localDateTime(listing.available_from),
    available_until: listing.available_until ? localDateTime(listing.available_until) : '',
    proof_available: listing.proof_available === null ? '' : listing.proof_available ? 'yes' : 'no',
  };
}

/** Edit an owner listing using its fresh revision and ordered image references. */
export function ListingEdit({ listingId }: { listingId?: string }) {
  const navigate = useNavigate();
  const [listing, setListing] = useState<ListingManagementView | null>(null);
  const [catalogue, setCatalogue] = useState<CatalogueView | null>(null);
  const [values, setValues] = useState<ListingFormValues | null>(null);
  const [images, setImages] = useState<ListingImageChoice[]>([]);
  const [loadError, setLoadError] = useState('');
  const [saveError, setSaveError] = useState('');
  const [errors, setErrors] = useState<ListingFormErrors>({});
  const [imagePending, setImagePending] = useState(false);
  const [imageUnresolved, setImageUnresolved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reload, setReload] = useState(0);
  const summary = useRef<HTMLDivElement>(null);
  const attempt = useRef<{ intent: string; operationId: string } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setListing(null);
    setCatalogue(null);
    setValues(null);
    setImages([]);
    setLoadError('');
    if (!listingId) {
      setLoadError('We couldn’t find that listing. Open Edit from one of your listings.');
      return () => controller.abort();
    }
    Promise.all([
      readOwnedListing(listingId, controller.signal),
      readCatalogue(controller.signal),
    ]).then(([owned, choices]) => {
      if (controller.signal.aborted) return;
      setListing(owned);
      setCatalogue(choices);
      setValues(listingValues(owned));
      setImages(owned.image_ids.map((image_id) => ({ source: 'existing' as const, image_id })));
    }).catch((failure: Error) => {
      if (!controller.signal.aborted) setLoadError(failure.message);
    });
    return () => controller.abort();
  }, [listingId, reload]);

  function change<K extends keyof ListingFormValues>(field: K, value: ListingFormValues[K]) {
    setValues((current) => current ? { ...current, [field]: value } : current);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!listing || !listingId || !values || saving || imagePending || imageUnresolved) return;
    const result = validateListingFields(values, Date.now(), true);
    const nextErrors = { ...result.errors };
    if (images.length < 1 || images.length > 8) {
      nextErrors.images = 'Keep between 1 and 8 photos on the listing.';
    }
    setErrors(nextErrors);
    setSaveError('');
    if (!result.fields || Object.keys(nextErrors).length) {
      requestAnimationFrame(() => summary.current?.focus());
      return;
    }
    const availableFrom = result.fields.available_from;
    if (!availableFrom) {
      setErrors({ available_from: 'Choose when the listing becomes available.' });
      return;
    }
    const intent = {
      ...result.fields,
      available_from: availableFrom,
      available_until: result.fields.available_until ?? null,
      pickup_area: result.fields.pickup_area ?? null,
      proof_available: result.fields.proof_available ?? null,
      expected_revision: listing.revision,
      images,
    };
    const serialized = JSON.stringify(intent);
    if (attempt.current?.intent !== serialized) {
      attempt.current = { intent: serialized, operationId: crypto.randomUUID() };
    }
    setSaving(true);
    try {
      await replaceListing(listingId, {
        ...intent,
        operation_id: attempt.current.operationId,
      });
      navigate(`/listings/${listingId}`, { state: { listingUpdated: true } });
    } catch (failure) {
      setSaveError((failure as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const invalid = (field: keyof ListingFormErrors) => ({
    'aria-invalid': errors[field] ? true as const : undefined,
    'aria-describedby': errors[field] ? `listing-${field}-error` : undefined,
  });
  const fieldError = (field: keyof ListingFormErrors) => errors[field]
    ? <p id={`listing-${field}-error`} className="listings-error">{errors[field]}</p> : null;

  return (
    <section className="listings-feature">
      <ListingNotice />
      {loadError ? (
        <div role="alert">
          <p>{loadError}</p>
          <Button onClick={() => setReload((current) => current + 1)}>Retry loading listing</Button>
        </div>
      ) : !listing || !catalogue || !values ? <p role="status">Loading your saved listing…</p> : (
        <form onSubmit={submit} noValidate className="listings-form" aria-busy={saving || imagePending}>
          <p className="listings-muted">Editing your saved listing · revision {listing.revision}</p>
          <p className="listings-price">Current asking price: {listingPrice(listing.asking_price_paise)}</p>
          {Object.keys(errors).length > 0 ? (
            <div ref={summary} tabIndex={-1} role="alert" className="listings-alert">
              <strong>Check these details before saving:</strong>
              <ul>{Object.entries(errors).map(([field, message]) => <li key={field}><a href={`#listing-${field}`}>{message}</a></li>)}</ul>
            </div>
          ) : null}
          {saveError ? (
            <div role="alert" className="listings-alert">
              <p>{saveError} Your unsaved changes are still here.</p>
              {saveError.includes('changed') || saveError.includes('Reload') ? (
                <Button variant="secondary" onClick={() => setReload((current) => current + 1)}>
                  Reload latest listing and discard these edits
                </Button>
              ) : null}
            </div>
          ) : null}
          <fieldset disabled={saving}>
            <legend>Listing details</legend>
            <label htmlFor="edit-listing-title">Title <span>(required)</span></label>
            <input id="edit-listing-title" value={values.title} onChange={(event) => change('title', event.target.value)} {...invalid('title')} />
            {fieldError('title')}
            <label htmlFor="edit-listing-description">Description <span>(required)</span></label>
            <textarea id="edit-listing-description" rows={5} value={values.description} onChange={(event) => change('description', event.target.value)} {...invalid('description')} />
            {fieldError('description')}
            <div className="listings-fields">
              <div>
                <label htmlFor="edit-listing-category">Item category <span>(required)</span></label>
                <select id="edit-listing-category" value={values.category_code} onChange={(event) => change('category_code', event.target.value)} {...invalid('category_code')}>
                  <option value="">Choose a category</option>
                  {!catalogue.categories.some((item) => item.code === listing.category_code) ? <option value={listing.category_code}>{listing.category_label} (not currently offered)</option> : null}
                  {catalogue.categories.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
                </select>
                {fieldError('category_code')}
              </div>
              <div>
                <label htmlFor="edit-listing-condition">Condition <span>(required)</span></label>
                <select id="edit-listing-condition" value={values.condition_code} onChange={(event) => change('condition_code', event.target.value)} {...invalid('condition_code')}>
                  <option value="">Choose a condition</option>
                  {catalogue.conditions.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
                </select>
                {fieldError('condition_code')}
              </div>
            </div>
            <label htmlFor="edit-listing-price">Asking price in rupees <span>(required; 0 means free)</span></label>
            <input id="edit-listing-price" type="text" inputMode="numeric" value={values.price_rupees} onChange={(event) => change('price_rupees', event.target.value)} {...invalid('price_rupees')} />
            {fieldError('price_rupees')}
            <label className="listings-check"><input type="checkbox" checked={values.negotiable} onChange={(event) => change('negotiable', event.target.checked)} />Price is negotiable</label>
            <label htmlFor="edit-listing-pickup">Pickup area <span>(optional)</span></label>
            <input id="edit-listing-pickup" value={values.pickup_area} onChange={(event) => change('pickup_area', event.target.value)} {...invalid('pickup_area')} />
            {fieldError('pickup_area')}
            <p className="listings-muted">Leave blank if you don’t want to specify a pickup area.</p>
            <div className="listings-fields">
              <div><label htmlFor="edit-listing-start">Available from <span>(required)</span></label><input id="edit-listing-start" type="datetime-local" value={values.available_from} onChange={(event) => change('available_from', event.target.value)} {...invalid('available_from')} />{fieldError('available_from')}</div>
              <div><label htmlFor="edit-listing-end">Available until <span>(optional)</span></label><input id="edit-listing-end" type="datetime-local" value={values.available_until} onChange={(event) => change('available_until', event.target.value)} {...invalid('available_until')} />{fieldError('available_until')}</div>
            </div>
            <label htmlFor="edit-listing-proof">Do you have proof of purchase? <span>(optional)</span></label>
            <select id="edit-listing-proof" value={values.proof_available} onChange={(event) => change('proof_available', event.target.value as ListingFormValues['proof_available'])}>
              <option value="">Prefer not to state</option><option value="yes">Yes</option><option value="no">No</option>
            </select>
            <p className="listings-muted">This remains your unverified statement.</p>
          </fieldset>
          <p className="listings-muted">Reorder the photos below. Removing a photo schedules its old file for cleanup after the save succeeds.</p>
          <ListingImageSet
            key={`${listingId}:${reload}`}
            images={images}
            onChange={(next) => {
              setImages(next);
              setErrors((current) => {
                const nextErrors = { ...current };
                delete nextErrors.images;
                return nextErrors;
              });
            }}
            onBusyChange={setImagePending}
            onPendingChange={setImageUnresolved}
            disabled={saving}
            error={errors.images}
          />
          <p role="status">{saving ? 'Saving your changes…' : imagePending ? 'Checking and saving selected photos…' : imageUnresolved ? 'Retry or remove unfinished photos before saving.' : `${images.length} of 8 confirmed photos selected.`}</p>
          <div className="listings-form-actions">
            <Button type="submit" disabled={saving || imagePending || imageUnresolved}>{saving ? 'Saving…' : 'Save changes'}</Button>
            <Link to="/my/listings">Cancel and return to My Listings</Link>
          </div>
        </form>
      )}
    </section>
  );
}
