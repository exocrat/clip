import { useEffect, useRef, useState, type FormEvent, type PropsWithChildren, type ReactNode } from 'react';
import { useNavigate } from 'react-router';
import { Button } from '../../shared/ui';
import { ListingNotice } from './ListingNotice';
import { MAX_MARKETPLACE_RUPEES } from '../../shared/money';
import { ListingImageSet, type ListingImageChoice } from './ListingImageSet';
import {
  createListing, readCatalogue,
  type CatalogueView,
} from './listingsApi';
import { validateListingForm, type ListingFormErrors, type ListingFormValues } from './listingForm';
import { newOperationId } from './operationId';
import './listings.css';

const emptyForm: ListingFormValues = {
  title: '', description: '', category_code: '', condition_code: '', price_rupees: '',
  original_price_rupees: '',
  negotiable: false, pickup_area: '', available_from: '', available_until: '', proof_available: '',
};

// Explain the approved catalogue meanings without changing its server-owned choices.
const conditionHelp: Record<string, string> = {
  new: 'Unused.',
  like_new: 'Previously used, with minimal visible wear.',
  good: 'Used, with normal signs of wear.',
  fair: 'Used, with substantial visible wear.',
};

/** Card-ready draft data passed to the route's public Search preview renderer. */
export type CreateListingPreviewData = {
  title: string;
  description: string;
  categoryLabel: string;
  conditionLabel: string;
  askingPricePaise: number | null;
  originalPricePaise: number | null;
  negotiable: boolean;
  pickupArea: string;
  photoUrl: string | null;
};

/** Create through the real Listings API; pending images never publish an incomplete row. */
export function CreateListing({ children, renderPreview }: PropsWithChildren<{
  renderPreview?: (draft: CreateListingPreviewData) => ReactNode;
}>) {
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
  const [imageUnresolved, setImageUnresolved] = useState(false);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const summary = useRef<HTMLDivElement>(null);
  // Preserve the exact key/intent across a manual retry after a lost response.
  const attempt = useRef<{ intent: string; operationId: string } | null>(null);

  // A save can finish after logout/account change unmounts this form. Preserve
  // its server outcome, but never navigate or update a replacement actor's UI.
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);


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

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (saving || imagePending || imageUnresolved) return;
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
      attempt.current = { intent, operationId: newOperationId() };
    }
    setSaving(true);
    try {
      const listing = await createListing({ ...result.intent, operation_id: attempt.current.operationId });
      if (!mounted.current) return;
      navigate(`/listings/${listing.listing_id}`, { state: { listingCreated: true } });
    } catch (error) {
      if (mounted.current) setSaveError((error as Error).message);
    } finally { if (mounted.current) setSaving(false); }
  }

  const invalid = (field: keyof ListingFormErrors) => {
    const ids = [
      field === 'title' ? 'listing-title-count' : '',
      field === 'description' ? 'listing-description-count' : '',
      field === 'pickup_area' ? 'listing-pickup-count' : '',
      errors[field] ? `listing-${field}-error` : '',
    ].filter(Boolean).join(' ');
    return {
    'aria-invalid': errors[field] ? true as const : undefined,
    'aria-describedby': ids || undefined,
    };
  };
  const fieldError = (field: keyof ListingFormErrors) => errors[field]
    ? <p id={`listing-${field}-error`} className="listings-error">{errors[field]}</p> : null;

  const parsedPrice = /^\d+$/.test(values.price_rupees) ? Number(values.price_rupees) * 100 : Number.NaN;
  const previewDraft: CreateListingPreviewData = {
    title: values.title,
    description: values.description,
    categoryLabel: catalogue?.categories.find((item) => item.code === values.category_code)?.label ?? '',
    conditionLabel: catalogue?.conditions.find((item) => item.code === values.condition_code)?.label ?? '',
    askingPricePaise: Number.isSafeInteger(parsedPrice) ? parsedPrice : null,
    originalPricePaise: /^\d+$/.test(values.original_price_rupees)
      && Number(values.original_price_rupees) > 0
      && Number(values.original_price_rupees) <= MAX_MARKETPLACE_RUPEES
      ? Number(values.original_price_rupees) * 100 : null,
    negotiable: values.negotiable,
    pickupArea: values.pickup_area,
    photoUrl: photoPreviewUrl,
  };

  return (
    <section className="listings-feature">
      <ListingNotice />
      {loadError ? (
        <div role="alert"><p>{loadError}</p><Button onClick={() => setReload((value) => value + 1)}>Retry loading choices</Button></div>
      ) : !catalogue ? <p role="status">Loading item categories and conditions…</p> : (
        <form onSubmit={submit} noValidate className="listings-form" aria-busy={saving || imagePending}>
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
            <input id="listing-title" maxLength={240} value={values.title} onChange={(event) => change('title', event.target.value)} {...invalid('title')} />
            {fieldError('title')}
            <p id="listing-title-count" className="listings-muted">{[...values.title.trim()].length}/120 characters</p>
            <label htmlFor="listing-description">Description <span>(required)</span></label>
            <textarea id="listing-description" rows={5} maxLength={10000} value={values.description} onChange={(event) => change('description', event.target.value)} {...invalid('description')} />
            {fieldError('description')}
            <p id="listing-description-count" className="listings-muted">{[...values.description.trim()].length}/5,000 characters</p>
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
            <input id="listing-price_rupees" type="text" inputMode="numeric" maxLength={8} value={values.price_rupees} onChange={(event) => change('price_rupees', event.target.value)} {...invalid('price_rupees')} />
            {fieldError('price_rupees')}
            <p className="listings-muted">Maximum ₹1,00,00,000.</p>
            <label htmlFor="listing-original_price_rupees">Original price <span>(optional, whole ₹)</span></label>
            <input id="listing-original_price_rupees" type="text" inputMode="numeric" maxLength={8} value={values.original_price_rupees} onChange={(event) => change('original_price_rupees', event.target.value)} {...invalid('original_price_rupees')} />
            {fieldError('original_price_rupees')}
            <p className="listings-muted">Seller-provided and not independently verified. Leave blank if you do not know or do not want to share it.</p>
            <label className="listings-check"><input type="checkbox" checked={values.negotiable} onChange={(event) => change('negotiable', event.target.checked)} />Price is negotiable</label>
            <label htmlFor="listing-pickup_area">Pickup area <span>(optional)</span></label>
            <input id="listing-pickup_area" maxLength={240} value={values.pickup_area} onChange={(event) => change('pickup_area', event.target.value)} {...invalid('pickup_area')} />
            {fieldError('pickup_area')}
            <p id="listing-pickup-count" className="listings-muted">{[...values.pickup_area.trim()].length}/120 characters</p>
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
          <ListingImageSet
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
            onPreviewImageChange={setPhotoPreviewUrl}
            disabled={saving}
            error={errors.images}
          />
          <p role="status">{saving ? 'Saving your listing…' : imagePending ? 'Uploading your photos…' : imageUnresolved ? 'Retry or remove unfinished photos before publishing.' : images.length ? `${images.length} photo${images.length === 1 ? '' : 's'} ready to publish.` : 'Add at least one photo before publishing.'}</p>
          {renderPreview ? (
            <>
              <Button type="button" variant="secondary" onClick={() => setPreviewOpen((open) => !open)}>
                {previewOpen ? 'Hide listing preview' : 'Preview listing'}
              </Button>
              {previewOpen ? <div className="listings-preview">{renderPreview(previewDraft)}</div> : null}
            </>
          ) : null}
          <Button type="submit" disabled={saving || imagePending || imageUnresolved}>{saving ? 'Saving…' : 'Publish listing'}</Button>
        </form>
      )}
      {children}
    </section>
  );
}
