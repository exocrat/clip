import type { ButtonHTMLAttributes } from 'react';
import './Button.css';

export type ButtonVariant = 'primary' | 'secondary';

export type ButtonProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  'className'
> & {
  className?: string;
  variant?: ButtonVariant;
};

/** A shared native button with consistent variants and accessible disabled styling. */
export function Button({
  className = '',
  disabled = false,
  type = 'button',
  variant = 'primary',
  ...buttonProps
}: ButtonProps) {
  const classes = ['ui-button', `ui-button--${variant}`, className]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      {...buttonProps}
      className={classes}
      disabled={disabled}
      type={type}
    />
  );
}
