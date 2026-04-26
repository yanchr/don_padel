import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Dev: same-origin `/api/*` → FastAPI (see README: uvicorn on :8000)
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      // Playtomic public web API (CORS off in dev)
      "/_pweb": {
        target: "https://playtomic.com",
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path.replace(/^\/_pweb/, ""),
      },
      "/_papi": {
        target: "https://api.playtomic.io",
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path.replace(/^\/_papi/, ""),
      },
    },
  },
})
