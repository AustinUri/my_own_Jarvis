# JARVIS Companion for Android — v26 security-first alpha

This project is intentionally narrow. It exposes **native/system calendar read access** and basic device status to a paired JARVIS PC. It does **not** request Accessibility, contacts, SMS, microphone, camera, location, device-admin, notification-listener, storage, or `WRITE_CALENDAR` permissions.

## Transport
The PC phone bridge listens only on `127.0.0.1:8766`. Use **Tailscale Serve**, not router port-forwarding and not Tailscale Funnel, to expose that local service to your private tailnet over HTTPS.

The app refuses non-HTTPS URLs and expects the `*.ts.net` address shown by JARVIS.

## Authentication
During a five-minute pairing window the phone creates an ECDSA P-256 identity key in **Android Keystore** and sends only the public key to the PC. Every later request is signed and includes a timestamp + nonce; the PC rejects invalid signatures, stale timestamps and nonce replays. The private identity key is non-exportable from the app under normal Android Keystore operation.

## Build
Open this `android_companion` folder in Android Studio, allow it to install Android SDK 35 if needed, then choose **Build > Build APK(s)**. No paid API is required.

This source bundle does not include a prebuilt APK because the current build environment does not contain the Android SDK/Gradle toolchain. Build and signing should happen on your own PC so your signing key never leaves your machine.
