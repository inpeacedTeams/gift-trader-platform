import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import "./select.css";

export type SelectOption = { value: string; label: string; hint?: string };
export type SelectGroup = { label: string; options: SelectOption[] };

type Props = {
  value: string;
  onChange: (value: string) => void;
  options?: SelectOption[];
  groups?: SelectGroup[];
  placeholder?: string;
  label?: string;
  disabled?: boolean;
};

/** Styled listbox that matches the app shell.
 *
 * Native selects render with OS chrome that ignores the dark theme, so this
 * keeps the visual language consistent while staying keyboard accessible.
 */
export function Select({ value, onChange, options, groups, placeholder = "Select", label, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const listId = useId();

  const flat = useMemo<SelectOption[]>(
    () => (groups ? groups.flatMap(group => group.options) : options ?? []),
    [groups, options]
  );
  const selected = flat.find(option => option.value === value) ?? null;

  useEffect(() => {
    if (!open) return;
    const index = flat.findIndex(option => option.value === value);
    setActive(index < 0 ? 0 : index);
  }, [open, value, flat]);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const commit = (next: string) => {
    onChange(next);
    setOpen(false);
  };

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (disabled) return;
    if (event.key === "Escape") return setOpen(false);
    if (!open && ["Enter", " ", "ArrowDown", "ArrowUp"].includes(event.key)) {
      event.preventDefault();
      return setOpen(true);
    }
    if (!open) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive(index => (index + 1) % flat.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive(index => (index - 1 + flat.length) % flat.length);
    } else if (event.key === "Home") {
      event.preventDefault();
      setActive(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setActive(flat.length - 1);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      const option = flat[active];
      if (option) commit(option.value);
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  };

  const renderOption = (option: SelectOption) => {
    const index = flat.indexOf(option);
    const isSelected = option.value === value;
    return (
      <li
        key={option.value}
        id={`${listId}-${index}`}
        role="option"
        aria-selected={isSelected}
        className={`ui-option${index === active ? " active" : ""}${isSelected ? " selected" : ""}`}
        onMouseEnter={() => setActive(index)}
        onMouseDown={event => event.preventDefault()}
        onClick={() => commit(option.value)}
      >
        <span className="ui-option-copy">
          {option.label}
          {option.hint && <small>{option.hint}</small>}
        </span>
        {isSelected && <Check size={13} />}
      </li>
    );
  };

  return (
    <div className={`ui-select${open ? " open" : ""}${disabled ? " disabled" : ""}`} ref={root}>
      <button
        type="button"
        className="ui-select-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={label}
        aria-activedescendant={open ? `${listId}-${active}` : undefined}
        disabled={disabled}
        onClick={() => setOpen(current => !current)}
        onKeyDown={onKeyDown}
      >
        <span className={selected ? "ui-value" : "ui-value muted"}>{selected?.label ?? placeholder}</span>
        <ChevronDown size={14} className="ui-caret" />
      </button>
      {open && (
        <ul className="ui-listbox" role="listbox" id={listId} tabIndex={-1}>
          {groups
            ? groups.map(group => (
                <li key={group.label} className="ui-group">
                  <span className="ui-group-label">{group.label}</span>
                  <ul role="group" aria-label={group.label}>
                    {group.options.map(renderOption)}
                  </ul>
                </li>
              ))
            : (options ?? []).map(renderOption)}
        </ul>
      )}
    </div>
  );
}
