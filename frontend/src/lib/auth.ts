import { api } from "./api";

interface AuthResponse {
  access_token: string;
  refresh_token: string;
}

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export async function login(email: string, password: string): Promise<User> {
  const tokens = await api.post<AuthResponse>("/api/v1/auth/login", { email, password });
  localStorage.setItem("access_token", tokens.access_token);
  localStorage.setItem("refresh_token", tokens.refresh_token);
  return api.get<User>("/api/v1/auth/me");
}

export async function register(email: string, password: string, fullName: string): Promise<User> {
  const tokens = await api.post<AuthResponse>("/api/v1/auth/register", {
    email,
    password,
    full_name: fullName,
  });
  localStorage.setItem("access_token", tokens.access_token);
  localStorage.setItem("refresh_token", tokens.refresh_token);
  return api.get<User>("/api/v1/auth/me");
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login";
}

export function isAuthenticated(): boolean {
  return typeof window !== "undefined" && !!localStorage.getItem("access_token");
}

export async function getMe(): Promise<User | null> {
  try {
    return await api.get<User>("/api/v1/auth/me");
  } catch {
    return null;
  }
}
