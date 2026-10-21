import { useEffect, useRef, useState, type FormEvent, type PropsWithChildren } from 'react';
import { useNavigate } from 'react-router';
import { Button } from '../../shared/ui';
import { ListingNotice } from './ListingNotice';
import { ListingImageSet, type ListingImageChoice } from './ListingImageSet';
import {
  createListing, isolatedListingsDemo, prepareDemoImage, readCatalogue,
  type CatalogueView,
} from './listingsApi';
import { validateListingForm, type ListingFormErrors, type ListingFormValues } from './listingForm';
import './listings.css';

const emptyForm: ListingFormValues = {
  title: '', description: '', category_code: '', condition_code: '', price_rupees: '',
  negotiable: false, pickup_area: '', available_from: '', available_until: '', proof_available: '',
};

// Explain the approved catalogue meanings without changing its server-owned choices.
const conditionHelp: Record<string, string> = {
  new: 'Unused.',
  like_new: 'Previously used, with minimal visible wear.',
  good: 'Used, with normal signs of wear.',
  fair: 'Used, with substantial visible wear.',
};

/** Create through the real Listings API; pending images never publish an incomplete row. */
export function CreateListing({ children }: PropsWithChildren) {
  const navigate = useNavigate();
  const [values, setValues] = useState(emptyForm);
  const [catalogue, setCatalogue] = useState<CatalogueView | null>(null);
  const [loadError, setLoadError] = useState('');
  const [reload, setReload] = useState(0);
  const [errors, setErrors] = useState<ListingFormErrors>({});
  const [saveError, setSaveError] = useState('');
  const [saving, setSaving] = useState(false);
  const [images, setImages] = useState<ListingImageChoice[]>([]);
  const [imagePending, setImagePending] = useState(false);
  const [imageError, setImageError] = useState('');
  const summary = useRef<HTMLDivElement>(null);
  // Preserve the exact key/intent across a manual retry after a lost response.
  const attempt = useRef<{ intent: string; operationId: string } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setCatalogue(null);
    setLoadError('');
    readCatalogue(controller.signal).then((result) => {
      if (!controller.signal.aborted) setCatalogue(result);
    }).catch((error: Error) => {
      if (!controller.signal.aborted) setLoadError(error.message);
    });
    return () => controller.abort();
  }, [reload]);

  function change<K extends keyof ListingFormValues>(field: K, value: ListingFormValues[K]) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function prepareImage() {
    setImagePending(true);
    setImageError('');
    try {
      const prepared = await prepareDemoImage();
      setImages((current) => current.length < 8
        ? [...current, { source: 'upload', upload_id: prepared.upload_id }]
        : current);
      setErrors((current) => ({ ...current, images: undefined }));
    }
    catch (error) { setImageError((error as Error).message); }
    finally { setImagePending(false); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (saving) return;
    const uploadIds = images.flatMap((image) => image.source === 'upload' ? [image.upload_id] : []);
    const result = validateListingForm(values, uploadIds);
    setErrors(result.errors);
    setSaveError('');
    if (!result.intent) {
      // Wait for the error summary to mount before moving keyboard focus.
      requestAnimationFrame(() => summary.current?.focus());
      return;
    }
    const intent = JSON.stringify(result.intent);
    if (attempt.current?.intent !== intent) {
      attempt.current = { intent, operationId: crypto.randomUUID() };
    }
    setSaving(true);
    try {
      const listing = await createListing({ ...result.intent, operation_id: attempt.current.operationId });
      navigate(`/listings/${listing.listing_id}`, { state: { listingCreated: true } });
    } catch (error) {
      setSaveError((error as Error).message);
    } finally { setSaving(false); }
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
        <div role="alert"><p>{loadError}</p><Button onClick={() => setReload((value) => value + 1)}>Retry loading choices</Button></div>
      ) : !catalogue ? <p role="status">Loading item categories and conditions…</p> : (
        <form onSubmit={submit} noValidate className="listings-form" aria-busy={saving}>
          {Object.keys(errors).length > 0 && (
            <div ref={summary} tabIndex={-1} role="alert" className="listings-alert">
              <strong>Check these details before publishing:</strong>
              <ul>{Object.entries(errors).map(([field, message]) => <li key={field}><a href={`#listing-${field}`}>{message}</a></li>)}</ul>
            </div>
          )}
          {saveError && <p role="alert" className="listings-alert">{saveError} Your entries are still here.</p>}
          <fieldset disabled={saving}>
            <legend>Describe your item</legend>
            <label htmlFor="listing-title">Title <span>(required)</span></label>
            <input id="listing-title" value={values.title} onChange={(event) => change('title', event.target.value)} {...invalid('title')} />
            {fieldError('title')}
            <label htmlFor="listing-description">Description <span>(required)</span></label>
            <textarea id="listing-description" rows={5} value={values.description} onChange={(event) => change('description', event.target.value)} {...invalid('description')} />
            {fieldError('description')}
            <div className="listings-fields">
              <div><label htmlFor="listing-category_code">Item category <span>(required)</span></label>
                <select id="listing-category_code" value={values.category_code} onChange={(event) => change('category_code', event.target.value)} {...invalid('category_code')}>
                  <option value="">Choose a category</option>{catalogue.categories.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
                </select>{fieldError('category_code')}</div>
              <div><label htmlFor="listing-condition_code">Condition <span>(required)</span></label>
                <select id="listing-condition_code" value={values.condition_code} onChange={(event) => change('condition_code', event.target.value)} {...invalid('condition_code')} aria-describedby={`listing-condition-help${errors.condition_code ? ' listing-condition_code-error' : ''}`}>
                  <option value="">Choose a condition</option>{catalogue.conditions.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
                </select>{fieldError('condition_code')}
                <p id="listing-condition-help" className="listings-muted">{conditionHelp[values.condition_code] ?? 'Choose the condition that best describes your item.'} Mention any defects in the description.</p>
              </div>
            </div>
            <label htmlFor="listing-price_rupees">Asking price in rupees <span>(required; 0 means free)</span></label>
            <input id="listing-price_rupees" type="text" inputMode="numeric" value={values.price_rupees} onChange={(event) => change('price_rupees', event.target.value)} {...invalid('price_rupees')} />
            {fieldError('price_rupees')}
            <label className="listings-check"><input type="checkbox" checked={values.negotiable} onChange={(event) => change('negotiable', event.target.checked)} />Price is negotiable</label>
            <label htmlFor="listing-pickup_area">Pickup area <span>(optional)</span></label>
            <input id="listing-pickup_area" value={values.pickup_area} onChange={(event) => change('pickup_area', event.target.value)} {...invalid('pickup_area')} />
            {fieldError('pickup_area')}
            <p className="listings-muted">Use a general area. Arrange exact collection details privately.</p>
            <div className="listings-fields">
              <div><label htmlFor="listing-available_from">Available from <span>(optional)</span></label>
                <input id="listing-available_from" type="datetime-local" value={values.available_from} onChange={(event) => change('available_from', event.target.value)} {...invalid('available_from')} />{fieldError('available_from')}</div>
              <div><label htmlFor="listing-available_until">Available until <span>(optional)</span></label>
                <input id="listing-available_until" type="datetime-local" value={values.available_until} onChange={(event) => change('available_until', event.target.value)} {...invalid('available_until')} />{fieldError('available_until')}</div>
            </div>
            <p className="listings-muted">Dates use your local time. With no start, availability begins when saved. With no end, there is no end date.</p>
            <label htmlFor="listing-proof_available">Do you have proof of purchase? <span>(optional)</span></label>
            <select id="listing-proof_available" value={values.proof_available} onChange={(event) => change('proof_available', event.target.value as ListingFormValues['proof_available'])}>
              <option value="">Prefer not to state</option><option value="yes">Yes</option><option value="no">No</option>
            </select>
            <p className="listings-muted">This is your statement; CLIP does not verify it. A buyer can ask for proof in chat.</p>
          </fieldset>
          {isolatedListingsDemo ? (
            <>
              <p className="listings-muted">Prepared image records let you try the 1–8 image flow. No photo file is uploaded or validated.</p>
              <ListingImageSet
                images={images}
                onChange={(next) => {
                  setImages(next);
                  setErrors((current) => ({ ...current, images: undefined }));
                }}
                onAddPrepared={prepareImage}
                adding={imagePending}
                disabled={saving}
                error={errors.images ?? imageError}
              />
            </>
          ) : (
            <fieldset id="listing-images">
              <legend>Listing photos</legend>
              <p>Photo uploads are not connected yet. Add at least one confirmed photo to publish.</p>
              {fieldError('images')}
            </fieldset>
          )}
          <p role="status">{saving ? 'Saving your listing…' : imagePending ? 'Image record pending — not published.' : images.length ? `${images.length} prepared image reference${images.length === 1 ? '' : 's'} ready; no photo files have been uploaded.` : 'Unpublished form — add at least one confirmed image.'}</p>
          <Button type="submit" disabled={saving || imagePending}>{saving ? 'Saving…' : 'Publish listing'}</Button>
        </form>
      )}
      {children}
    </section>
  );
}
