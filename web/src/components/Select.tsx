import { KeyboardEvent, useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import "./select.css";

export type SelectOption = { value: string; label: string; hint?: string };
export type SelectGroup = { label: string; options: SelectOption[] };

type Props = {
  value: string;
  onChange: (value: string) => void;
  options?: SelectOption[];
  groups?: SelectGroup[];
  label?: string;
  /** Render the label inside the trigger, for filter bars where height matters. */
  inlineLabel?: boolean;
  placeholder?: string;
  disabled?: boolean;
};

type Row = { kind: "group"; label: string } | { kind: "option"; option: SelectOption; index: number };

function buildRows(options?: SelectOption[], groups?: SelectGroup[]): Row[] {
  const rows: Row[] = [];
  let index = 0;
  if (groups) {
    for (const group of groups) {
      rows.push({ kind: "group", label: group.label });
      for (const option of group.options) rows.push({ kind: "option", option, index: index++ });
    }
    return rows;
  }
  for (const option of options ?? []) rows.push({ kind: "option", option, index: index++ });
  return rows;
}

/** Listbox that keeps the product's own surface language instead of OS chrome. */
export function Select({ value, onChange, options, groups, label, inlineLabel, placeholder = "Select", disabled }: Props) {
  const id = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const rows = useMemo(() => buildRows(options, groups), [options, groups]);
  const flat = useMemo(() => rows.flatMap(row => (row.kind === "option" ? [row.option] : [])), [rows]);
  const selectedIndex = Math.max(0, flat.findIndex(option => option.value === value));
  const selected = flat[selectedIndex];

  useEffect(() => {
    if (!open) return;
    setActive(selectedIndex);
    const dismiss = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [open, selectedIndex]);

  useEffect(() => {
    if (!open) return;
    listRef.current
      ?.querySelector<HTMLElement>(`[data-index="${active}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [open, active]);

  const commit = (option: SelectOption) => {
    onChange(option.value);
    setOpen(false);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (disabled) return;
    const keys = ["ArrowDown", "ArrowUp", "Home", "End", "Enter", " "];
    if (!open) {
      if (!keys.includes(event.key)) return;
      event.preventDefault();
      setOpen(true);
      return;
    }
    if (event.key === "Escape" || event.key === "Tab") {
      setOpen(false);
      return;
    }
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    if (event.key === "Enter" || event.key === " ") {
      const option = flat[active];
      if (option) commit(option);
      return;
    }
    const last = flat.length - 1;
    if (event.key === "Home") setActive(0);
    else if (event.key === "End") setActive(last);
    else if (event.key === "ArrowDown") setActive(current => (current >= last ? 0 : current + 1));
    else setActive(current => (current <= 0 ? last : current - 1));
  };

  return (
    <div
      className={`ui-select${open ? " open" : ""}${inlineLabel ? " inline" : ""}`}
      ref={rootRef}
      onKeyDown={onKeyDown}
    >
      {label && !inlineLabel && (
        <span className="ui-select-label" id={`${id}-label`}>
          {label}
        </span>
      )}
      <button
        type="button"
        className="ui-select-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-labelledby={label ? `${id}-label ${id}-value` : undefined}
        aria-activedescendant={open ? `${id}-opt-${active}` : undefined}
        disabled={disabled}
        onClick={() => setOpen(current => !current)}
      >
        {inlineLabel && label && (
          <span className="ui-select-inline-label" id={`${id}-label`}>
            {label}
          </span>
        )}
        <span className="ui-select-value" id={`${id}-value`}>
          {selected?.label ?? placeholder}
        </span>
        <ChevronDown size={15} className="ui-select-chevron" aria-hidden="true" />
      </button>
      {open && (
        <div
          className="ui-select-menu"
          role="listbox"
          ref={listRef}
          aria-labelledby={label ? `${id}-label` : undefined}
        >
          {rows.map((row, position) =>
            row.kind === "group" ? (
              <div className="ui-select-group" key={`group-${row.label}`} role="presentation">
                {row.label}
              </div>
            ) : (
              <button
                type="button"
                key={row.option.value}
                id={`${id}-opt-${row.index}`}
                data-index={row.index}
                role="option"
                aria-selected={row.option.value === value}
                className={`ui-select-option${row.index === active ? " active" : ""}`}
                style={{ animationDelay: `${Math.min(position, 8) * 18}ms` }}
                onPointerEnter={() => setActive(row.index)}
                onClick={() => commit(row.option)}
              >
                <span className="ui-select-option-copy">
                  {row.option.label}
                  {row.option.hint && <small>{row.option.hint}</small>}
                </span>
                {row.option.value === value && <Check size={14} className="ui-select-check" />}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
