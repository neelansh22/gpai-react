import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, AlertTriangle, Info, XCircle } from "lucide-react";
import { useSdodState } from "../state/SdodState";

const ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const TONE_CLASSES = {
  success: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
  error: "bg-rose-500/15 text-rose-300 ring-rose-500/30",
  warning: "bg-amber-500/15 text-amber-300 ring-amber-500/30",
  info: "bg-brand-500/15 text-brand-300 ring-brand-500/30",
};

export default function SdodToast() {
  const { toast } = useSdodState();
  const Icon = toast ? ICONS[toast.tone] || Info : Info;

  return (
    <div className="pointer-events-none fixed bottom-6 right-6 z-50">
      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.96 }}
            className={`pointer-events-auto flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium shadow-xl ring-1 backdrop-blur-xl ${
              TONE_CLASSES[toast.tone] || TONE_CLASSES.info
            }`}
          >
            <Icon className="h-4 w-4" />
            {toast.message}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
