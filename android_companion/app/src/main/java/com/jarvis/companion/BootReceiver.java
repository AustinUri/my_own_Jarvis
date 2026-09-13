package com.jarvis.companion;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public final class BootReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        if (!new PhoneApiClient(context).prefs().getBoolean("companion_enabled", false)) return;
        if (new PhoneApiClient(context).prefs().getString("device_id", "").isEmpty()) return;
        try {
            context.startForegroundService(new Intent(context, JarvisForegroundService.class));
        } catch (Exception ignored) {
            // Android may temporarily defer a foreground service during boot.
            // START_STICKY and the next manual app launch remain safe fallbacks.
        }
    }
}
