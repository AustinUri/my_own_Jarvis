# JARVIS v26 — Start Here

## 1. Keep the working version as a backup
Do not destroy a working v25/v24 folder while testing v26. Extract v26 to a fresh folder first.

## 2. Install/update the Windows Python environment
Open PowerShell in the JARVIS v26 folder:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
```

v26 adds `cryptography` for signed phone requests and `keyring` for safer Google OAuth token storage.

## 3. LM Studio and web search
Keep the existing Qwen model downloaded:

```powershell
lms ps
```

Expected identifier:

```text
jarvis-qwen
```

JARVIS can manage LM Studio and SearXNG/Docker in the background. If needed for diagnosis:

```powershell
.\scripts\doctor.ps1
```

## 4. Launch

```powershell
.\scripts\run_jarvis.ps1
```

JARVIS Core continues to run in the tray after the Control Center is closed.

## 5. Default location
v26 defaults weather to:

```text
Netanya, Israel
```

You can change it later in Settings.

## 6. Daily briefing
The briefing is dynamic. Israel, IDF/security, football, Champions League, Formula 1, AI/technology and world news are **interest/ranking hints**, not mandatory fixed sections.

JARVIS should choose the genuinely important items it can support from retrieved evidence, summarize them locally, and skip weak/failed categories without showing internal SearXNG configuration messages.

## 7. Calendar behavior
Preferred order in v26:

```text
Native phone/system calendar -> Google Calendar backup -> unavailable
```

Public web search is never used as a substitute for your private calendar.

### Google backup
Google remains optional. Put your Desktop App OAuth client JSON at:

```text
%APPDATA%\Jarvis\credentials\google_calendar_client.json
```

Then click Google backup in the Calendar widget or say:

```text
Jarvis, connect my Google Calendar.
```

Normal operation is one sign-in followed by silent token refresh. v26 prefers Windows keyring/Credential Manager for the token. If an older v25 token JSON exists, JARVIS attempts to migrate it.

## 8. Agent Activity
Open **Agent Activity**. The trace now reads in execution order from top to bottom:

```text
#001 INPUT       RECEIVED   User request
#002 REASONING   WORKING    Agent model round 1
#003 TOOL        START      answer_web_question
#004 WEB         WORKING    Web research ...
#005 TOOL        SUCCESS    answer_web_question via searxng
#006 REASONING   WORKING    Agent model round 2
#007 OUTPUT      SUCCESS    Jarvis response
```

The point of this tab is to make the agent understandable instead of showing an unordered wall of diagnostic text.

# PHONE COMPANION — SECURITY-FIRST ALPHA

## 9. What v26 phone access can do
The Android companion source is in:

```text
android_companion\
```

The first version deliberately exposes only:

- native/system calendar **READ**
- basic device information

It does **not** request Accessibility, SMS, contacts, microphone, camera, storage, device-admin or calendar-write permission.

This is intentional. Do not grant powerful phone-control permissions until the narrow read-only bridge has been tested successfully.

## 10. Private remote transport
For remote use away from home, v26 is designed for a private Tailscale network. It does **not** require router port forwarding and JARVIS must not use Tailscale Funnel/public exposure.

Install the official Tailscale client on the Windows PC and Android phone, and sign both into the same personal tailnet.

Then either open **Phone Link** in JARVIS and press:

```text
Prepare private link
```

or run once:

```powershell
.\scripts\setup_phone_link.ps1
```

The PC phone bridge itself listens only on:

```text
127.0.0.1:8766
```

Tailscale Serve supplies private HTTPS access inside your tailnet.

## 11. Build the Android app
This ZIP includes source, not a prebuilt APK. Build/sign the APK on your own PC so your application signing key stays under your control.

1. Install Android Studio from the official Android developer site.
2. Open the `android_companion` folder as a project.
3. Allow Android Studio to install Android SDK 35 / required build tools.
4. Build **Build > Build APK(s)**.
5. Install that APK on your Android phone.

The companion is intentionally simple and has no paid SDK/API dependency.

## 12. Pair the phone
1. Make sure Tailscale is connected on PC and phone.
2. Open JARVIS **Phone Link**.
3. Press **Prepare private link**.
4. Press **Create pairing code**.
5. In the phone companion enter the HTTPS `*.ts.net` server URL shown by JARVIS and the eight-digit pairing code.
6. Grant **Calendar read** only.
7. Start the secure companion service.

The pairing code is short-lived and one-use. The phone creates its identity private key in Android Keystore and sends only the public key to the PC. Later requests are signed; stale/replayed requests are rejected.

## 13. Revoke the phone
At any time open Phone Link and choose **Revoke phone**. Stopping the Android companion also stops JARVIS from retrieving native phone calendar data.

## 14. Important security statement
No software can honestly promise a zero-percent chance of a security vulnerability. v26 reduces risk by minimizing permissions, keeping the bridge localhost-only, using private-network HTTPS, signing phone requests, preventing replay, and not exposing general phone-control capabilities.

The correct next step is to test this read-only build first. Camera, notifications, phone app control and calendar writes should be separate future capabilities with separate explicit permissions.
