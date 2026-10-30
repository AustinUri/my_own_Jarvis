package com.jarvis.companion;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.telecom.TelecomManager;

public final class JarvisPhoneActions {

    public static final class Result {
        public final boolean ok;
        public final String message;

        Result(boolean ok, String message) {
            this.ok = ok;
            this.message = message == null ? "" : message;
        }
    }

    private JarvisPhoneActions() {
    }

    public static Result placeCarrierCall(
            Context context,
            String rawNumber
    ) {
        if (context == null) {
            return new Result(false, "Context unavailable");
        }

        String number =
                rawNumber == null
                        ? ""
                        : rawNumber.trim();

        if (number.isEmpty()) {
            return new Result(false, "Phone number is empty");
        }

        if (context.checkSelfPermission(
                Manifest.permission.CALL_PHONE
        ) != PackageManager.PERMISSION_GRANTED) {
            return new Result(
                    false,
                    "CALL_PHONE permission is not granted"
            );
        }

        TelecomManager telecomManager =
                context.getSystemService(
                        TelecomManager.class
                );

        if (telecomManager == null) {
            return new Result(
                    false,
                    "Telecom service unavailable"
            );
        }

        try {
            telecomManager.placeCall(
                    Uri.fromParts(
                            "tel",
                            number,
                            null
                    ),
                    Bundle.EMPTY
            );

            return new Result(
                    true,
                    "Carrier call request submitted"
            );

        } catch (SecurityException ex) {
            return new Result(
                    false,
                    "Call permission denied: "
                            + ex.getClass()
                            .getSimpleName()
            );

        } catch (Exception ex) {
            return new Result(
                    false,
                    "Call failed: "
                            + ex.getClass()
                            .getSimpleName()
            );
        }
    }
}
