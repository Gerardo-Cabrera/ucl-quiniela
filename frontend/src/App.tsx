import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { ErrorBoundary } from "react-error-boundary";
import { Toaster } from "react-hot-toast";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/store/authStore";
import { useInactivityLogout } from "@/hooks";
import { Navbar } from "@/components/Navbar";
import { ErrorFallback } from "@/components/ErrorFallback";
import { TOASTER_STYLE } from "@/config";

import LoginPage        from "@/pages/Login";
import Dashboard        from "@/pages/Dashboard";
import MatchesPage      from "@/pages/Matches";
import MyPredictionsPage from "@/pages/MyPredictions";
import Top8Page         from "@/pages/Top8";
import AciertosPage     from "@/pages/Aciertos";
import JornadaPage      from "@/pages/Jornada";
import MvpsPage         from "@/pages/Mvps";
import ProfilePage      from "@/pages/Profile";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

function ProtectedLayout() {
  const { isAuthenticated } = useAuthStore();
  useInactivityLogout();  // cierra la sesión tras 1 h de inactividad
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return (
    <div className="min-h-screen ucl-stars-bg">
      <Navbar />
      <main className="lg:pl-56 pt-14 pb-20 lg:pt-0 lg:pb-0">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/"            element={<Dashboard />} />
            <Route path="/matches"     element={<MatchesPage />} />
            <Route path="/predictions" element={<MyPredictionsPage />} />
            <Route path="/top8"        element={<Top8Page />} />
            <Route path="/aciertos"    element={<AciertosPage />} />
            <Route path="/jornada"     element={<JornadaPage />} />
            <Route path="/mvps"        element={<MvpsPage />} />
            <Route path="/profile"     element={<ProfilePage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  const { t } = useTranslation();
  // Título del navegador vía i18n (el <title> de index.html es solo el fallback
  // estático que se ve antes de que cargue React).
  useEffect(() => { document.title = t("brand.appTitle"); }, [t]);

  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/*"     element={<ProtectedLayout />} />
          </Routes>
        </BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{ style: TOASTER_STYLE }}
        />
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
