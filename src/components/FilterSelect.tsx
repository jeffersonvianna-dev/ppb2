import { useEffect, useId, useMemo, useRef, useState } from 'react';

export interface FilterOption {
  value: string;
  label: string;
}

interface FilterSelectProps {
  label: string;
  options: FilterOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  searchPlaceholder: string;
  compact?: boolean;
}

export default function FilterSelect({
  label,
  options,
  value,
  onChange,
  placeholder,
  searchPlaceholder,
  compact = false,
}: FilterSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const rootRef = useRef<HTMLDivElement | null>(null);
  const listboxId = useId();

  useEffect(() => {
    if (!isOpen) return;
    const handler = (ev: MouseEvent) => {
      if (!rootRef.current?.contains(ev.target as Node)) setIsOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((o) => o.label.toLowerCase().includes(q));
  }, [options, query]);

  const selectedLabel = options.find((o) => o.value === value)?.label || placeholder;

  return (
    <div className={`field field-inline field-combobox ${compact ? 'field-compact' : ''}`} ref={rootRef}>
      <label>{label}</label>
      <button
        type="button"
        className={`combobox-trigger ${isOpen ? 'open' : ''}`}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        onClick={() => {
          setIsOpen((c) => !c);
          if (isOpen) setQuery('');
        }}
      >
        <span>{selectedLabel}</span>
        <span className="combobox-count">{options.length}</span>
      </button>

      {isOpen && (
        <div className="combobox-panel">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={searchPlaceholder}
            className="combobox-search"
            autoFocus
          />
          <div className="combobox-meta">
            {visible.length} de {options.length} opções
          </div>
          <div className="combobox-list" id={listboxId} role="listbox" aria-label={label}>
            {visible.map((opt) => (
              <button
                type="button"
                key={opt.value}
                className={`combobox-option ${opt.value === value ? 'selected' : ''}`}
                onClick={() => {
                  onChange(opt.value);
                  setQuery('');
                  setIsOpen(false);
                }}
              >
                {opt.label}
              </button>
            ))}
            {visible.length === 0 && <div className="combobox-empty">Nenhuma opção.</div>}
          </div>
        </div>
      )}
    </div>
  );
}
