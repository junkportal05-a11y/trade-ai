export const BRIEF_TIMEOUT_MS = 20000;

export function briefErrorMessage(err) {
  if (err && err.name === 'AbortError') {
    return 'Daily Market Briefing timed out. Tap RETRY to try again.';
  }
  if (err && typeof err.message === 'string' && err.message.startsWith('HTTP')) {
    return 'Daily Market Briefing failed (server error). Tap RETRY to try again.';
  }
  return 'Failed to fetch Daily Market Briefing. Check connection and tap RETRY.';
}
