import { useEffect, useId, useRef, useState } from "react";
import { Info } from "lucide-react";

const ACCENTS = {
  brand: { bar: "from-brand-400 to-purple-500", ring: "ring-brand-500/30", text: "text-brand-300" },
  sky: { bar: "from-sky-400 to-cyan-500", ring: "ring-sky-500/30", text: "text-sky-300" },
  emerald: { bar: "from-emerald-400 to-teal-500", ring: "ring-emerald-500/30", text: "text-emerald-300" },
};

const SIDES = {
  right: "left-full top-1/2 ml-2 -translate-y-1/2 origin-left",
  left: "right-full top-1/2 mr-2 -translate-y-1/2 origin-right",
  top: "bottom-full left-1/2 mb-2 -translate-x-1/2 origin-bottom",
  bottom: "top-full left-1/2 mt-2 -translate-x-1/2 origin-top",
};

/**
 * Smart, click-or-hover tooltip used across all three apps to surface
 * contextual guidance and highlight feature value without cluttering the UI.
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
  const wrapRef = useRef(null);
  const id = useId();
  const a = ACCENTS[accent] || ACCENTS.brand;

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

  return (
    <span
      ref={wrapRef}
      className={`relative inline-flex ${className}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
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
      <div
        id={id}
        role="tooltip"
        className={`pointer-events-none absolute z-50 w-64 rounded-xl border border-slate-700/80 bg-slate-900/95 p-3 text-left shadow-2xl ring-1 backdrop-blur-md transition-all duration-150 ease-out ${a.ring} ${SIDES[side]} ${
          open ? "pointer-events-auto scale-100 opacity-100" : "scale-95 opacity-0"
        }`}
      >
        <div className={`mb-1.5 h-0.5 w-8 rounded-full bg-gradient-to-r ${a.bar}`} />
        {title && <p className="mb-1 text-xs font-semibold text-white">{title}</p>}
        <p className="text-[11px] leading-relaxed text-slate-300">{content}</p>
      </div>
    </span>
  );
}
