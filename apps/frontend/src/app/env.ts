const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

if (!apiBaseUrl) {
  throw new Error("Missing VITE_API_BASE_URL. Create apps/frontend/.env.local from .env.example.");
}

export const env = {
  apiBaseUrl: apiBaseUrl.replace(/\/+$/, ""),
};
