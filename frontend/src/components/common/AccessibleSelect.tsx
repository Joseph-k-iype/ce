/**
 * Accessible Select Component
 * ===========================
 * WCAG 2.1 AA compliant multi-select dropdown wrapper.
 *
 * Features:
 * - Full keyboard navigation support
 * - Screen reader announcements
 * - Error state handling
 * - Required field indicators
 * - Help text support
 */

import Select, { type MultiValue } from 'react-select';
import { reactSelectStyles, reactSelectTheme, reactSelectDarkStyles, reactSelectDarkTheme } from '../../styles/reactSelectTheme';

interface Option {
  value: string;
  label: string;
}

interface AccessibleSelectProps {
  id: string;
  label: string;
  value: string[];
  options: Option[];
  onChange: (values: string[]) => void;
  helpText?: string;
  error?: string;
  required?: boolean;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  /** 'dark' applies dark-background-safe styles for wizard steps on dark cards */
  variant?: 'light' | 'dark';
}

/**
 * AccessibleSelect Component
 *
 * A fully accessible multi-select dropdown that wraps react-select
 * with proper ARIA attributes and WCAG-compliant styling.
 *
 * @example
 * ```tsx
 * <AccessibleSelect
 *   id="data-categories"
 *   label="Data Categories"
 *   value={selectedCategories}
 *   options={[
 *     { value: 'health', label: 'Health Data' },
 *     { value: 'financial', label: 'Financial Data' }
 *   ]}
 *   onChange={setSelectedCategories}
 *   helpText="Select all applicable categories"
 *   required
 * />
 * ```
 */
export function AccessibleSelect({
  id,
  label,
  value,
  options,
  onChange,
  helpText,
  error,
  required = false,
  placeholder = 'Select...',
  disabled = false,
  className = '',
  variant = 'light',
}: AccessibleSelectProps) {
  const helpId = `${id}-help`;
  const errorId = `${id}-error`;

  // Convert string values to Select options format
  const selectedOptions = value.map(v => {
    const option = options.find(opt => opt.value === v);
    return option || { value: v, label: v };
  });

  const handleChange = (selected: unknown) => {
    const opts = selected as MultiValue<Option>;
    onChange((opts || []).map(s => s.value));
  };

  return (
    <div className={`mb-4 ${className}`}>
      {/* Label */}
      <label
        htmlFor={id}
        className={`block text-sm font-medium mb-2 ${variant === 'dark' ? 'text-gray-200' : 'text-gray-700'
          }`}
      >
        {label}
        {required && (
          <span
            className="text-red-500 ml-1"
            aria-label="required"
          >
            *
          </span>
        )}
      </label>

      {/* Select Component */}
      <Select
        isMulti
        inputId={id}
        options={options}
        value={selectedOptions}
        onChange={handleChange}
        styles={variant === 'dark' ? reactSelectDarkStyles : reactSelectStyles}
        theme={variant === 'dark' ? reactSelectDarkTheme : reactSelectTheme}
        placeholder={placeholder}
        isDisabled={disabled}
        // Accessibility attributes
        aria-label={label}
        aria-describedby={
          `${helpText ? helpId : ''} ${error ? errorId : ''}`.trim() || undefined
        }
        aria-required={required}
        aria-invalid={!!error}
      />

      {/* Help Text (shown when no error) */}
      {helpText && !error && (
        <p
          id={helpId}
          className={`mt-1 text-xs ${variant === 'dark' ? 'text-gray-400' : 'text-gray-500'
            }`}
        >
          {helpText}
        </p>
      )}

      {/* Error Message (takes precedence over help text) */}
      {error && (
        <p
          id={errorId}
          className={`mt-1 text-xs font-semibold ${variant === 'dark' ? 'text-red-400' : 'text-red-600'
            }`}
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
}
