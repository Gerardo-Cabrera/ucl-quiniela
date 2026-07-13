import { useState } from "react";
import { X } from "lucide-react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { useAuthStore } from "@/store/authStore";
import { apiErrorMessage } from "@/lib/apiError";
import { Spinner } from "@/components/ui";

/** Modal para cambiar la contraseña estando logueado (verifica la actual). */
export function ChangePasswordModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const { changePassword } = useAuthStore();
  const [current, setCurrent] = useState("");
  const [next, setNext]       = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setError("");
    if (next.length < 6)   { setError(t("auth.errPasswordShort")); return; }
    if (next !== confirm)  { setError(t("auth.changePassword.mismatch")); return; }
    if (next === current)  { setError(t("auth.changePassword.sameAsCurrent")); return; }
    setLoading(true);
    try {
      await changePassword(current, next);
      toast.success(t("auth.changePassword.success"));
      onClose();
    } catch (err: any) {
      setError(apiErrorMessage(err, t("auth.genericError")));
    } finally {
      setLoading(false);
    }
  };

  const field = (label: string, value: string, onChange: (v: string) => void) => (
    <div>
      <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{label}</label>
      <input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        placeholder="••••••••"
        className="input-base w-full"
        aria-label={label}
      />
    </div>
  );

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-ucl-navy/80 backdrop-blur-sm" onClick={onClose} />
      <div className="card relative w-full max-w-sm p-6 border-ucl-gold/20">
        <button
          onClick={onClose}
          aria-label={t("common.close")}
          className="absolute top-4 right-4 text-ucl-silver/60 hover:text-ucl-white transition-colors"
        >
          <X size={18} />
        </button>
        <h2 className="font-display text-2xl mb-5">{t("auth.changePassword.title")}</h2>

        <div className="space-y-4">
          {field(t("auth.changePassword.current"), current, setCurrent)}
          {field(t("auth.changePassword.new"), next, setNext)}
          {field(t("auth.changePassword.confirm"), confirm, setConfirm)}

          {error && (
            <div role="alert" className="bg-red-900/20 border border-red-500/30 rounded-lg px-4 py-2.5 text-red-400 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={submit}
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2 mt-2"
          >
            {loading ? <><Spinner size="sm" /> {t("common.loading")}</> : t("auth.changePassword.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}
