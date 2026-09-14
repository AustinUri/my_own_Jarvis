# JARVIS v26 — Free Secure Mobile Foundation + Ordered Agent Activity

## Why this release exists
v25 proved the background runtime, daily intelligence, persistent modes and managed local services. v26 focuses on two priorities from real use: a safer path toward remote phone integration without paid AI APIs, and a much more precise Agent Activity view.

## Agent Activity — ordered execution timeline
- Agent Activity is no longer a reverse dump of raw log strings.
- Every visible activity receives a stable sequence number and local timestamp.
- Activity is displayed oldest-to-newest so the execution path reads naturally from top to bottom.
- Categories include INPUT, REASONING, TOOL, WEB, RESEARCH, PHONE, VISION, SYSTEM, OUTPUT and ERROR.
- Status tags distinguish RECEIVED, WORKING, START, SUCCESS, WARNING, DENIED and ERROR.
- User requests and final Jarvis replies appear in the trace.
- Agent model rounds are shown.
- Tool requests and tool completions are separate ordered steps.
- Raw logs are still retained internally for diagnostics.

## Free / local-first policy
- No Fish Audio or other paid AI/TTS service is required.
- Existing local LM Studio / Qwen remains the primary model.
- SearXNG remains the primary free local web-search layer.
- Open-Meteo remains the weather source with Netanya, Israel as the default home location.
- Daily briefing interests are ranking hints, not mandatory sections.
- Daily briefing silently skips failed searches instead of showing internal search-engine configuration errors to the user.

## Calendar hierarchy
1. Native/system phone calendar when the trusted Android companion is connected.
2. Google Calendar as an optional backup.
3. No public web-search substitute for personal calendar data.

The phone calendar is read-only in v26. Calendar write permission is intentionally not requested yet.

## Google Calendar backup
- OAuth is designed for one-time user sign-in with automatic refresh-token reuse.
- v26 prefers Windows keyring / Credential Manager storage for the Google token.
- Existing v25 token JSON is migrated to keyring on a best-effort basis.
- Google Calendar is explicitly presented as a backup rather than the primary calendar.

## Android companion — security-first alpha
The included `android_companion` source is deliberately narrow:
- Native/system calendar READ permission.
- Basic device information.
- No Accessibility Service.
- No SMS, contacts, microphone, camera, storage, device-admin, or WRITE_CALENDAR permission.
- `allowBackup=false`.
- Cleartext HTTP is disabled.
- Remote server URL must be HTTPS on a `*.ts.net` hostname.
- The companion initiates outbound polling; JARVIS does not open a listener on the phone.
- The phone creates an ECDSA P-256 private identity key in Android Keystore.
- The private key is not sent to the PC.
- Every post-pairing request is signed and includes timestamp + nonce replay protection.
- Pairing uses an 8-digit, single-use, short-lived code and server-side rate limiting.
- The PC phone bridge binds only to `127.0.0.1`.
- Recommended remote transport is Tailscale Serve, not router port-forwarding and not Tailscale Funnel.
- Paired phones can be revoked from the Control Center.

## Phone Link workspace
- New Phone Link widget shows paired/connected state, transport, security summary and calendar availability.
- `Prepare private link` configures tailnet-only Tailscale Serve when possible.
- `Create pairing code` creates a five-minute one-use pairing code.
- New Mobile workspace combines Phone Link, Calendar, JARVIS Core and Conversation.

## Workspace/profile migration
- v25 custom workspaces are preserved when migrating to v26.
- v26 stores browser-side workspace state under new `jarvis26.*` keys while importing previous layouts.

## Not yet enabled on the phone
For security, v26 deliberately does NOT expose:
- camera access
- microphone access
- notification reading
- Accessibility / arbitrary UI automation
- app launching/control
- SMS/messages
- contacts
- file/storage access
- native calendar writing

Those capabilities should be added individually only after the read-only companion has been tested successfully on the real phone.

## Validation performed in the build environment
- Python source compilation check.
- Workspace JavaScript syntax check with Node.
- Static workspace HTTP endpoints checked where dependencies permit.
- Android source is included but no APK is shipped because the build environment does not contain the Android SDK/Gradle toolchain. The APK should be built and signed on the user's own Windows PC with Android Studio so the signing key never leaves that PC.
