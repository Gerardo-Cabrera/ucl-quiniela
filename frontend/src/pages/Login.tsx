import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/store/authStore";
import { apiErrorMessage } from "@/lib/apiError";
import { Spinner } from "@/components/ui";

type Mode = "login" | "register" | "reset";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage() {
  const { t } = useTranslation();
  const [mode, setMode]           = useState<Mode>("login");
  const [identifier, setIdentifier] = useState("");   // login: email, alias o equipo
  const [email, setEmail]         = useState("");     // registro / recuperación
  const [password, setPassword]   = useState("");     // en "reset" es la nueva contraseña
  const [teamName, setTeamName]   = useState("");
  const [alias, setAlias]         = useState("");
  const [error, setError]         = useState("");
  const [notice, setNotice]       = useState("");     // mensaje de éxito (verde)
  const [loading, setLoading]     = useState(false);

  const { login, register, resetPassword } = useAuthStore();
  const navigate = useNavigate();

  const switchMode = (m: Mode) => { setMode(m); setError(""); setNotice(""); };

  // Validaciones cliente (feedback inmediato); el backend aplica las mismas reglas.
  const registerError = (): string | null => {
    if (teamName.trim().length < 3) return t("auth.errTeamShort");
    if (alias.trim() && alias.trim().length < 3) return t("auth.errAliasShort");
    if (!EMAIL_RE.test(email)) return t("auth.errEmailInvalid");
    if (password.length < 6) return t("auth.errPasswordShort");
    return null;
  };
  const resetErrorMsg = (): string | null => {
    if (!EMAIL_RE.test(email)) return t("auth.errEmailInvalid");
    if (teamName.trim().length < 3) return t("auth.errTeamShort");
    if (password.length < 6) return t("auth.errPasswordShort");
    return null;
  };

  const handleSubmit = async () => {
    setError(""); setNotice("");
    if (mode === "register") { const invalid = registerError(); if (invalid) { setError(invalid); return; } }
    if (mode === "reset")    { const invalid = resetErrorMsg(); if (invalid) { setError(invalid); return; } }
    setLoading(true);
    try {
      if (mode === "login") {
        await login(identifier, password);
        navigate("/");
      } else if (mode === "register") {
        await register(teamName, email, password, alias || undefined);
        setPassword(""); setMode("login"); setError(""); setNotice(t("auth.registerSuccess"));
      } else {
        await resetPassword(email, teamName, password);
        setPassword(""); setMode("login"); setError(""); setNotice(t("auth.resetSuccess"));
      }
    } catch (err: any) {
      setError(apiErrorMessage(err, t("auth.genericError")));
    } finally {
      setLoading(false);
    }
  };

  const field = (
    label: string, value: string, onChange: (v: string) => void,
    { type = "text", placeholder = "", aria = label }: { type?: string; placeholder?: string; aria?: string } = {},
  ) => (
    <div>
      <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        placeholder={placeholder}
        className="input-base w-full"
        aria-label={aria}
      />
    </div>
  );

  return (
    <div className="min-h-screen ucl-stars-bg flex items-center justify-center p-4">
      {/* Stars decorativas */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-ucl-gold/30 rounded-full animate-pulse"
            style={{
              top:  `${Math.random() * 100}%`,
              left: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 3}s`,
            }}
          />
        ))}
      </div>

      <div className="w-full max-w-sm relative">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="font-display text-6xl text-ucl-gold tracking-widest">{t("brand.name")}</h1>
          <p className="text-ucl-silver/70 font-mono text-sm mt-1">{t("brand.tagline")}</p>
          <div className="mt-3 flex justify-center gap-1">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-ucl-gold/40" />
            ))}
          </div>
        </div>

        {/* Card */}
        <div className="card border-ucl-gold/20 p-6 shadow-[0_0_60px_rgba(201,168,76,0.08)]">
          {/* Tabs */}
          <div className="flex mb-6 bg-ucl-navy/60 rounded-lg p-1">
            {(["login", "register"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => switchMode(m)}
                className={`flex-1 py-2 text-sm rounded-md transition-all duration-200 ${
                  mode === m
                    ? "bg-ucl-gold text-ucl-navy font-bold"
                    : "text-ucl-silver hover:text-ucl-white"
                }`}
              >
                {m === "login" ? t("auth.tabLogin") : t("auth.tabRegister")}
              </button>
            ))}
          </div>

          {mode === "reset" && (
            <p className="text-xs text-ucl-silver/60 mb-4 -mt-2">{t("auth.resetHint")}</p>
          )}

          <div className="space-y-4">
            {mode === "login" &&
              field(t("auth.identifier"), identifier, setIdentifier, { placeholder: t("auth.identifierPlaceholder") })}

            {mode === "register" && (
              <>
                {field(t("auth.yourTeam"), teamName, setTeamName, { placeholder: t("auth.teamPlaceholder") })}
                {field(t("auth.alias"), alias, setAlias, { placeholder: t("auth.aliasPlaceholder") })}
                {field(t("auth.email"), email, setEmail, { type: "email", placeholder: t("auth.emailPlaceholder"), aria: t("auth.emailAria") })}
              </>
            )}

            {mode === "reset" && (
              <>
                {field(t("auth.email"), email, setEmail, { type: "email", placeholder: t("auth.emailPlaceholder"), aria: t("auth.emailAria") })}
                {field(t("auth.yourTeam"), teamName, setTeamName, { placeholder: t("auth.teamPlaceholder") })}
              </>
            )}

            {field(
              mode === "reset" ? t("auth.changePassword.new") : t("auth.password"),
              password, setPassword, { type: "password", placeholder: "••••••••", aria: t("auth.password") },
            )}

            {error && (
              <div role="alert" className="bg-red-900/20 border border-red-500/30 rounded-lg px-4 py-2.5 text-red-400 text-sm">
                {error}
              </div>
            )}
            {notice && !error && (
              <div role="status" className="bg-green-900/20 border border-green-500/30 rounded-lg px-4 py-2.5 text-green-400 text-sm">
                {notice}
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 mt-2"
            >
              {loading ? <><Spinner size="sm" /> {t("common.loading")}</> :
               mode === "login" ? t("auth.submitLogin") :
               mode === "register" ? t("auth.submitRegister") : t("auth.resetSubmit")}
            </button>

            {mode === "login" && (
              <button type="button" onClick={() => switchMode("reset")}
                className="w-full text-center text-xs text-ucl-silver/60 hover:text-ucl-gold transition-colors">
                {t("auth.forgotPassword")}
              </button>
            )}
            {mode === "reset" && (
              <button type="button" onClick={() => switchMode("login")}
                className="w-full text-center text-xs text-ucl-silver/60 hover:text-ucl-gold transition-colors">
                {t("auth.backToLogin")}
              </button>
            )}
          </div>
        </div>

        <p className="text-center text-ucl-silver/40 text-xs mt-6 font-mono">
          {t("brand.copyright")}
        </p>
      </div>
    </div>
  );
}
