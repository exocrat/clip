import { Button } from './Button';
import './SegmentedControl.css';

export type SegmentedControlOption<Value extends string> = {
  value: Value;
  label: string;
};

export type SegmentedControlProps<Value extends string> = {
  label: string;
  options: readonly SegmentedControlOption<Value>[];
  value: Value;
  onValueChange: (value: Value) => void;
  className?: string;
};

/** A controlled single-choice view switch; callers own its state and content. */
export function SegmentedControl<Value extends string>({
  label,
  options,
  value,
  onValueChange,
  className = '',
}: SegmentedControlProps<Value>) {
  const classes = ['segmented-control', className].filter(Boolean).join(' ');

  return (
    <fieldset aria-label={label} className={classes}>
      {options.map((option) => (
        <Button
          key={option.value}
          aria-pressed={option.value === value}
          className="segmented-control__option"
          onClick={() => onValueChange(option.value)}
          variant="secondary"
        >
          {option.label}
        </Button>
      ))}
    </fieldset>
  );
}
