#!/usr/bin/env node
/**
 * Guard script to prevent accidental VITE_API_URL or VITE_WS_URL replacements
 * that would reintroduce cross-origin CORS errors.
 *
 * Exit codes:
 *   0 - OK (both variables are empty as expected for production)
 *   1 - ERROR (VITE_API_URL or VITE_WS_URL is set to a non-empty value)
 *
 * This script is used as a "prebuild" hook so that Vercel CI will fail fast.
 */

const API_URL = process.env.VITE_API_URL;
const WS_URL = process.env.VITE_WS_URL;

function isNonEmptyString(value) {
  return value && value.trim().length > 0;
}

/**
 * In production we expect these to be empty strings.
 * If VITE_API_URL is set to a real URL (common mistake when copying .env.example)
 * we want to abort the build early with a clear error.
 */
if (isNonEmptyString(API_URL)) {
  console.error('❌ Error: VITE_API_URL is set. It must be empty in production.');
  console.error('   The frontend proxy expects VITE_API_URL to be empty so that same‑origin requests');
  console.error('   can be rewritten to the HF Space backend. Remove any value from VITE_API_URL.');
  console.error('   See README for details.');
  process.exit(1);
}

/**
 * Same guard for websocket URL – it must point exactly to the HF space we control,
 * not a hard‑coded cross‑origin domain. If it's set to a non‑empty value that differs
 * from the whitelisted HF URL, abort.
 */
const WHITELISTED_WS = 'wss://apextrade-core-trade-ai-backend.hf.space';
if (isNonEmptyString(WS_URL) && WS_URL !== WHITELISTED_WS) {
  console.error('❌ Error: VITE_WS_URL is set to an unexpected value.');
  console.error(`   Allowed value: ${WHITELISTED_WS}`);
  console.error('   Update the whitelist check or the URL as needed.');
  process.exit(1);
}

/**
 * If we get here everything is as expected.
 */
process.exit(0);