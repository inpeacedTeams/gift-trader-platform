import { useState } from "react";

/** Marketplace images 404 often enough that a silent fallback is required. */
export function GiftImage({ src, alt, className }: { src?: string | null; alt: string; className?: string }) {
  const [broken, setBroken] = useState(false);
  if (!src || broken) {
    return (
      <div className={`gift-image placeholder ${className ?? ""}`.trim()} aria-hidden="true">
        ✦
      </div>
    );
  }
  return (
    <img
      className={`gift-image ${className ?? ""}`.trim()}
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setBroken(true)}
    />
  );
}
