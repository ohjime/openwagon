# RESEARCH_STRATEGY

When reproducing an external product interface, map the reachable experience before implementing it:

1. Capture the initial screen at its native viewport.
2. Inspect every visible control and follow each safe, non-destructive transition.
3. Capture each reachable state and note destinations that require authentication, credentials, payment, or form submission rather than completing those actions.
4. Record controls, transitions, visible content, visual hierarchy, and any capture limitations in a focused research note.
5. Include a user-flow diagram, a state-transition diagram, and screen wireframes so implementation can proceed without reopening the reference site.

Keep this research separate from the replica implementation. Never submit login, password-reset, sign-up, or purchase forms with user data unless that action is explicitly authorized.

## Production research safeguards

Treat production systems as read-only unless the user explicitly authorizes a specific write action.

- Prefer a dedicated read-only role or account.
- Observe through screenshots, visible UI text, URLs, and safe navigation only.
- Do not create, edit, assign, dispatch, cancel, complete, or otherwise change live trips.
- Do not submit forms, toggle persistent settings, drag records, acknowledge alerts, or activate controls whose outcome is not known to be read-only.
- Before any action that could transmit data or alter production state, stop and obtain explicit confirmation for that exact action.
- Record observations with a timestamp, route, screenshot, visible controls, and any uncertainty.
- Research one screen at a time and return to a known-safe landing screen after each observation.
