import { Sparkles } from "lucide-react";
import type { GiftCard, RarityTier } from "../types";
import { formatRarity } from "../format";
import "../rarity.css";

/** Tier bounds mirror app/market/rarity.py. Keep the two in step. */
export const RARITY_TIERS: { value: RarityTier; label: string; hint: string }[] = [
  { value: "legendary", label: "Legendary", hint: "0.3% of the collection or rarer" },
  { value: "rare", label: "Rare", hint: "up to 1%" },
  { value: "uncommon", label: "Uncommon", hint: "up to 5%" },
  { value: "common", label: "Common", hint: "above 5%" },
];

type Traits = Pick<
  GiftCard,
  "model" | "model_rarity" | "backdrop" | "backdrop_rarity" | "symbol" | "symbol_rarity" | "rarity_tier"
>;
type Trait = { slot: string; name: string; percent: string };

function rated(gift: Traits): Trait[] {
  return [
    { slot: "Model", name: gift.model, percent: gift.model_rarity },
    { slot: "Backdrop", name: gift.backdrop, percent: gift.backdrop_rarity },
    { slot: "Symbol", name: gift.symbol, percent: gift.symbol_rarity },
  ].filter((item): item is Trait => Boolean(item.name && item.percent));
}

/** The scarcest trait we know of, or null when no source published one. */
export function rarestTrait(gift: Traits): Trait | null {
  const candidates = rated(gift);
  if (!candidates.length) return null;
  return candidates.reduce((best, item) => (Number(item.percent) < Number(best.percent) ? item : best));
}

/** Badge for the trait that makes a gift worth more than its floor.
 *
 * Silent on common and on unrated gifts: a badge that says nothing trains
 * people to ignore the badge that says something.
 */
export function RarityBadge({ gift, inline = false }: { gift: Traits; inline?: boolean }) {
  const rarest = rarestTrait(gift);
  const percent = rarest ? formatRarity(rarest.percent) : null;
  if (!rarest || !percent || !gift.rarity_tier || gift.rarity_tier === "common") return null;
  return (
    <span
      className={`rarity-badge ${gift.rarity_tier}${inline ? " inline" : ""}`}
      title={`${rarest.slot} ${rarest.name}: ${percent} of the collection carries it`}
    >
      <Sparkles size={11} /> {rarest.name} {percent}
    </span>
  );
}

/** All three traits laid out, including the ones we do not have yet.
 *
 * A missing trait is stated as missing rather than left off the page, so a
 * gap in the data never reads as a plain gift.
 */
export function TraitGrid({ gift }: { gift: Traits }) {
  const slots = [
    { label: "Model", name: gift.model, percent: gift.model_rarity },
    { label: "Backdrop", name: gift.backdrop, percent: gift.backdrop_rarity },
    { label: "Symbol", name: gift.symbol, percent: gift.symbol_rarity },
  ];
  return (
    <div className="trait-grid">
      {slots.map(slot => {
        const percent = formatRarity(slot.percent);
        const scarce = slot.percent !== null && slot.percent !== undefined && Number(slot.percent) <= 1;
        return (
          <div className="trait" key={slot.label}>
            <span>{slot.label}</span>
            <strong className={slot.name ? undefined : "unknown"}>{slot.name ?? "not published"}</strong>
            <small className={scarce ? "scarce" : undefined}>
              {percent ? `${percent} of the collection` : "rarity unknown"}
            </small>
          </div>
        );
      })}
    </div>
  );
}
