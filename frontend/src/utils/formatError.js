/**
 * Converts any API error response, FastAPI detail array/object, or JS exception
 * into a safe, human-readable primitive string to prevent React rendering Error #31.
 */
export function formatError(err, fallback = "An unexpected error occurred.") {
  if (!err) return fallback;
  if (typeof err === "string") return err;
  
  if (Array.isArray(err)) {
    return err
      .map(item => {
        if (typeof item === "string") return item;
        if (typeof item === "object" && item !== null) {
          return item.msg || item.message || JSON.stringify(item);
        }
        return String(item);
      })
      .join(", ");
  }

  if (typeof err === "object" && err !== null) {
    if (err.detail) {
      return formatError(err.detail, fallback);
    }
    if (err.message && typeof err.message === "string") {
      return err.message;
    }
    if (err.msg && typeof err.msg === "string") {
      return err.msg;
    }
    try {
      return JSON.stringify(err);
    } catch (_) {
      return fallback;
    }
  }

  return String(err);
}
