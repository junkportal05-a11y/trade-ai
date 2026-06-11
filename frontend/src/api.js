let base = import.meta.env.VITE_API_URL || "";
if (base && !base.startsWith("http")) {
  base = "https://" + base;
}
if (base.endsWith("/")) {
  base = base.slice(0, -1);
}
export const API_BASE_URL = base;
