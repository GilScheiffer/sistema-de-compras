import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Publicado em https://gilscheiffer.github.io/sistema-de-compras/
export default defineConfig({
  base: "/sistema-de-compras/",
  plugins: [react()],
});
