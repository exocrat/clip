import { useId } from 'react';
import './MultiChoiceDropdown.css';

export type MultiChoiceOption = { value: string; label: string };

export type MultiChoiceDropdownProps = {
  label: string;
  options: readonly MultiChoiceOption[];
  values: readonly string[];
  onValuesChange: (values: string[]) => void;
  emptyLabel?: string;
  disabled?: boolean;
};

/**
 * Accessible controlled multi-choice dropdown for independent filter values.
 * The native details/summary keeps it keyboard-operable; each choice is a
 * checkbox. Empty selection is interpreted by the caller as no restriction.
 */
export function MultiChoiceDropdown({
  label,
  options,
  values,
  onValuesChange,
  emptyLabel = 'All',
  disabled = false,
}: MultiChoiceDropdownProps) {
  const id = useId();
  const selected = new Set(values);
  const selectedLabels = options.filter((option) => selected.has(option.value)).map((option) => option.label);
  const summary = selectedLabels.length === 0
    ? emptyLabel
    : selectedLabels.length <= 2
      ? selectedLabels.join(', ')
      : `${selectedLabels.length} selected`;

  function toggle(value: string, checked: boolean) {
    const next = new Set(values);
    if (checked) next.add(value);
    else next.delete(value);
    onValuesChange(options.filter((option) => next.has(option.value)).map((option) => option.value));
  }

  return (
    <details className="ui-multi-choice" data-disabled={disabled || undefined}>
      <summary aria-disabled={disabled} tabIndex={disabled ? -1 : undefined}>
        <span className="ui-multi-choice__label">{label}</span>
        <span className="ui-multi-choice__selection">{summary}</span>
      </summary>
      <fieldset className="ui-multi-choice__options" disabled={disabled}>
        <legend className="ui-multi-choice__sr-only">Choose {label.toLocaleLowerCase()}</legend>
        {options.map((option, index) => (
          <label className="ui-multi-choice__option" key={option.value}>
            <input
              checked={selected.has(option.value)}
              id={`${id}-${index}`}
              onChange={(event) => toggle(option.value, event.currentTarget.checked)}
              type="checkbox"
              value={option.value}
            />
            <span>{option.label}</span>
          </label>
        ))}
        {values.length > 0 && (
          <button className="ui-multi-choice__clear" onClick={() => onValuesChange([])} type="button">
            Clear selection
          </button>
        )}
      </fieldset>
    </details>
  );
}
