package com.jarvis.companion;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

/**
 * Restarts the JARVIS Oracle Device Bus link after a normal phone reboot
 * or after the app package is replaced by an update.
 *
 * The receiver only starts the service when this phone was already paired
 * and the companion link was enabled by the user/app.
 */
public final class BootReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        if (context == null || intent == null) {
            return;
        }

        String action = intent.getAction();
        if (!Intent.ACTION_BOOT_COMPLETED.equals(action)
                && !Intent.ACTION_MY_PACKAGE_REPLACED.equals(action)) {
            return;
        }

        SharedPreferences prefs = context.getSharedPreferences(
                PhoneApiClient.PREFS,
                Context.MODE_PRIVATE
        );

        if (!prefs.getBoolean("paired_v30", false)
                || !prefs.getBoolean("companion_enabled", false)) {
            return;
        }

        // Do not start a useless foreground service if the encrypted
        // Oracle device credential is missing or cannot be read.
        try {
            String token = SecureTokenStore.load(context);
            if (token == null || token.trim().isEmpty()) {
                return;
            }
        } catch (Exception ignored) {
            return;
        }

        Intent serviceIntent = new Intent(
                context,
                JarvisForegroundService.class
        );

        if (Build.VERSION.SDK_INT >= 26) {
            context.startForegroundService(serviceIntent);
        } else {
            context.startService(serviceIntent);
        }
    }
}
