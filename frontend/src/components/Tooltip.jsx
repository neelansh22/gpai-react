import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Info } from "lucide-react";

const ACCENTS = {
  brand: { bar: "from-brand-400 to-purple-500", ring: "ring-brand-500/30", text: "text-brand-300" },
  sky: { bar: "from-sky-400 to-cyan-500", ring: "ring-sky-500/30", text: "text-sky-300" },
  emerald: { bar: "from-emerald-400 to-teal-500", ring: "ring-emerald-500/30", text: "text-emerald-300" },
};

const GAP = 10;
const WIDTH = 260;

/**
 * Smart, click-or-hover tooltip used across all three apps to surface
 * contextual guidance and highlight feature value without cluttering the UI.
 *
 * Renders its popup content into a portal on document.body with fixed
 * positioning computed from the trigger's bounding rect, so it can never be
 * clipped or hidden behind scrollable panels/sidebars/cards.
 */
export default function Tooltip({
  content,
  title,
  side = "right",
  accent = "brand",
  icon: IconComp = Info,
  iconClassName = "h-3.5 w-3.5",
  className = "",
}) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState(null);
  const wrapRef = useRef(null);
  const btnRef = useRef(null);
  const id = useId();
  const a = ACCENTS[accent] || ACCENTS.brand;

  const computePosition = useCallback(() => {
    const el = btnRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    let top;
    let left;
    let placedSide = side;

    if (side === "right" || side === "left") {
      top = rect.top + rect.height / 2;
      if (side === "right") {
        left = rect.right + GAP;
        if (left + WIDTH > window.innerWidth - 8) placedSide = "left";
      }
      if (placedSide === "left") {
        left = rect.left - GAP - WIDTH;
        if (left < 8) {
          // fall back to right if left doesn't fit either
          placedSide = "right";
          left = rect.right + GAP;
        }
      }
    } else {
      left = rect.left + rect.width / 2;
      if (side === "bottom") {
        top = rect.bottom + GAP;
        if (top > window.innerHeight - 60) placedSide = "top";
      }
      if (placedSide === "top") {
        top = rect.top - GAP;
      }
    }

    setCoords({ top, left, placedSide });
  }, [side]);

  useLayoutEffect(() => {
    if (!open) return undefined;
    computePosition();
    const onScroll = () => computePosition();
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onScroll);
    };
  }, [open, computePosition]);

  useEffect(() => {
    if (!open) return undefined;
    function onDocClick(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    }
    function onKey(e) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const placedSide = coords?.placedSide || side;
  const transformClass =
    placedSide === "right"
      ? "-translate-y-1/2 origin-left"
      : placedSide === "left"
      ? "-translate-x-full -translate-y-1/2 origin-right"
      : placedSide === "top"
      ? "-translate-x-1/2 -translate-y-full origin-bottom"
      : "-translate-x-1/2 origin-top";

  return (
    <span
      ref={wrapRef}
      className={`relative inline-flex ${className}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        ref={btnRef}
        type="button"
        aria-describedby={id}
        aria-label={title ? `About ${title}` : "More information"}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className={`inline-flex h-4 w-4 items-center justify-center rounded-full text-slate-500 transition-colors hover:text-white focus:outline-none focus-visible:${a.text}`}
      >
        <IconComp className={iconClassName} />
      </button>
      {open &&
        coords &&
        createPortal(
          <div
            id={id}
            role="tooltip"
            style={{ position: "fixed", top: coords.top, left: coords.left, width: WIDTH }}
            className={`pointer-events-none z-[9999] rounded-xl border border-slate-700/80 bg-slate-900/95 p-3 text-left shadow-2xl ring-1 backdrop-blur-md transition-all duration-150 ease-out ${a.ring} ${transformClass} scale-100 opacity-100`}
          >
            <div className={`mb-1.5 h-0.5 w-8 rounded-full bg-gradient-to-r ${a.bar}`} />
            {title && <p className="mb-1 text-xs font-semibold text-white">{title}</p>}
            <p className="text-[11px] leading-relaxed text-slate-300">{content}</p>
          </div>,
          document.body
        )}
    </span>
  );
}

