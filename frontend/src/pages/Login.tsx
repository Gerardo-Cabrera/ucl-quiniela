import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/store/authStore";
import { Spinner } from "@/components/ui";

type Mode = "login" | "register";

// Extrae un mensaje legible del error de axios. `detail` es string en nuestras
// HTTPException; en un 422 de Pydantic es una lista {msg, loc} (se toma el primero,
// quitando el prefijo "Value error, " de los validadores propios).
function apiErrorMessage(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return (detail[0]?.msg ?? "").replace(/^Value error, /, "") || fallback;
  }
  return fallback;
}

export default function LoginPage() {
  const { t } = useTranslation();
  const [mode, setMode]           = useState<Mode>("login");
  const [identifier, setIdentifier] = useState("");   // login: email, alias o equipo
  const [email, setEmail]         = useState("");     // registro
  const [password, setPassword]   = useState("");
  const [teamName, setTeamName]   = useState("");
  const [alias, setAlias]         = useState("");
  const [error, setError]         = useState("");
  const [loading, setLoading]     = useState(false);

  const { login, register } = useAuthStore();
  const navigate = useNavigate();

  // Validación de registro (feedback inmediato en español). El backend aplica las
  // mismas reglas como garantía.
  const registerError = (): string | null => {
    if (teamName.trim().length < 3) return t("auth.errTeamShort");
    if (alias.trim() && alias.trim().length < 3) return t("auth.errAliasShort");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return t("auth.errEmailInvalid");
    if (password.length < 6) return t("auth.errPasswordShort");
    return null;
  };

  const handleSubmit = async () => {
    setError("");
    if (mode === "register") {
      const invalid = registerError();
      if (invalid) { setError(invalid); return; }
    }
    setLoading(true);
    try {
      if (mode === "login") {
        await login(identifier, password);
      } else {
        await register(teamName, email, password, alias || undefined);
        setMode("login");
        setError("");
        return;
      }
      navigate("/");
    } catch (err: any) {
      setError(apiErrorMessage(err, t("auth.genericError")));
    } finally {
      setLoading(false);
    }
  };

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
                onClick={() => { setMode(m); setError(""); }}
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

          <div className="space-y-4">
            {mode === "login" ? (
              <div>
                <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{t("auth.identifier")}</label>
                <input
                  type="text"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                  placeholder={t("auth.identifierPlaceholder")}
                  className="input-base w-full"
                  aria-label={t("auth.identifier")}
                />
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{t("auth.yourTeam")}</label>
                  <input
                    type="text"
                    value={teamName}
                    onChange={(e) => setTeamName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                    placeholder={t("auth.teamPlaceholder")}
                    className="input-base w-full"
                    aria-label={t("auth.yourTeam")}
                  />
                </div>

                <div>
                  <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{t("auth.alias")}</label>
                  <input
                    type="text"
                    value={alias}
                    onChange={(e) => setAlias(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                    placeholder={t("auth.aliasPlaceholder")}
                    className="input-base w-full"
                    aria-label={t("auth.alias")}
                  />
                </div>

                <div>
                  <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{t("auth.email")}</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                    placeholder={t("auth.emailPlaceholder")}
                    className="input-base w-full"
                    aria-label={t("auth.emailAria")}
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{t("auth.password")}</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                placeholder="••••••••"
                className="input-base w-full"
                aria-label={t("auth.password")}
              />
            </div>

            {error && (
              <div role="alert" className="bg-red-900/20 border border-red-500/30 rounded-lg px-4 py-2.5 text-red-400 text-sm">
                {error}
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 mt-2"
            >
              {loading ? <><Spinner size="sm" /> {t("common.loading")}</> :
               mode === "login" ? t("auth.submitLogin") : t("auth.submitRegister")}
            </button>
          </div>
        </div>

        <p className="text-center text-ucl-silver/40 text-xs mt-6 font-mono">
          {t("brand.copyright")}
        </p>
      </div>
    </div>
  );
}
