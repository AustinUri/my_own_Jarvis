package com.jarvis.companion;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;

/**
 * Capability gate for future AI call recording / transcription.
 *
 * Standard third-party dialers cannot assume they can capture the carrier
 * call downlink. Full telephony capture requires privileged platform access
 * (CAPTURE_AUDIO_OUTPUT) or a vendor-supported recording/export path.
 *
 * This class intentionally does NOT fake a recorder. It gives the future
 * call-summary pipeline one truthful place to decide which capture backend
 * is available on the device.
 */
public final class JarvisCallRecordingCapability {

    public enum Mode {
        PRIVILEGED_TELEPHONY_CAPTURE,
        VENDOR_RECORDING_IMPORT,
        UNAVAILABLE
    }

    private JarvisCallRecordingCapability() {
    }

    public static boolean hasPrivilegedTelephonyCapture(
            Context context
    ) {
        if (context == null) {
            return false;
        }

        return context.checkSelfPermission(
                Manifest.permission.CAPTURE_AUDIO_OUTPUT
        ) == PackageManager.PERMISSION_GRANTED;
    }

    public static Mode detect(Context context) {
        if (hasPrivilegedTelephonyCapture(context)) {
            return Mode.PRIVILEGED_TELEPHONY_CAPTURE;
        }

        // Samsung/vendor recording import is deliberately not claimed until
        // we prove a stable, supported file/content-provider path on this S25.
        return Mode.UNAVAILABLE;
    }

    public static String reason(Context context) {
        if (hasPrivilegedTelephonyCapture(context)) {
            return "Privileged telephony audio capture available";
        }

        return "Carrier downlink capture is not exposed to this third-party "
                + "dialer; use a proven Samsung/vendor recording import or "
                + "privileged telephony capture backend before enabling AI summaries";
    }
}
