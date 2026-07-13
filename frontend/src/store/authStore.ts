import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/types";
import apiClient from "@/api/client";
import { AUTH_STORAGE_KEY } from "@/config";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  register: (teamName: string, email: string, password: string, alias?: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  resetPassword: (email: string, teamName: string, newPassword: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (identifier, password) => {
        const { data } = await apiClient.post("/api/auth/login", { identifier, password });
        set({ user: data.user, token: data.access_token, isAuthenticated: true });
      },

      register: async (team_name, email, password, alias) => {
        const { data } = await apiClient.post("/api/auth/register", { team_name, email, password, alias });
        set({ user: data });
      },

      changePassword: async (currentPassword, newPassword) => {
        await apiClient.post("/api/auth/change-password", {
          current_password: currentPassword, new_password: newPassword,
        });
      },

      resetPassword: async (email, teamName, newPassword) => {
        await apiClient.post("/api/auth/reset-password", {
          email, team_name: teamName, new_password: newPassword,
        });
      },

      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: AUTH_STORAGE_KEY,
      partialize: (state) => ({ user: state.user, token: state.token, isAuthenticated: state.isAuthenticated }),
    }
  )
);
