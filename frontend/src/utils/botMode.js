// The personal-workstation UI is paper-only. The backend also enforces this,
// but the client must never ask for a live bot session.
export function buildBotStartPayload() {
  return { paper: true };
}
