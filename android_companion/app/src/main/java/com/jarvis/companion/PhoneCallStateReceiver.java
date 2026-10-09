package com.jarvis.companion;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.provider.ContactsContract;
import android.telephony.TelephonyManager;

public final class PhoneCallStateReceiver extends android.content.BroadcastReceiver {

    private static final long DUPLICATE_WINDOW_MS = 1500L;

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) return;
        if (!TelephonyManager.ACTION_PHONE_STATE_CHANGED.equals(intent.getAction())) return;

        String rawState = intent.getStringExtra(TelephonyManager.EXTRA_STATE);
        if (rawState == null || rawState.isEmpty()) return;

        String state = normalizeState(rawState);
        String number = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER);
        if (number == null) number = "";

        SharedPreferences prefs = context.getSharedPreferences(
                PhoneApiClient.PREFS,
                Context.MODE_PRIVATE
        );

        long now = System.currentTimeMillis();
        String previousState = prefs.getString("phase2_last_call_state", "");
        String previousNumber = prefs.getString("phase2_last_call_number", "");
        long previousAt = prefs.getLong("phase2_last_call_event_ms", 0L);

        if (state.equals(previousState)
                && (number.isEmpty() || number.equals(previousNumber))
                && now - previousAt < DUPLICATE_WINDOW_MS) {
            return;
        }

        String direction = prefs.getString("phase2_active_call_direction", "unknown");
        if ("ringing".equals(state)) {
            direction = "incoming";
            prefs.edit().putString("phase2_active_call_direction", direction).apply();
        } else if ("idle".equals(state)) {
            prefs.edit().remove("phase2_active_call_direction").apply();
        }

        String effectiveNumber = number;
        if (effectiveNumber.isEmpty()) {
            effectiveNumber = prefs.getString("phase2_active_call_number", "");
        } else {
            prefs.edit().putString("phase2_active_call_number", effectiveNumber).apply();
        }

        String callerName = lookupContactName(context, effectiveNumber);

        prefs.edit()
                .putString("phase2_last_call_state", state)
                .putString("phase2_last_call_number", effectiveNumber)
                .putLong("phase2_last_call_event_ms", now)
                .apply();

        if ("idle".equals(state)) {
            prefs.edit().remove("phase2_active_call_number").apply();
        }

        Intent serviceIntent = new Intent(context, JarvisForegroundService.class);
        serviceIntent.setAction(JarvisForegroundService.ACTION_PHONE_STATE_EVENT);
        serviceIntent.putExtra("call_state", state);
        serviceIntent.putExtra("call_direction", direction);
        serviceIntent.putExtra("call_number", effectiveNumber);
        serviceIntent.putExtra("caller_name", callerName);
        serviceIntent.putExtra("occurred_at_ms", now);

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(serviceIntent);
            } else {
                context.startService(serviceIntent);
            }
        } catch (Exception ignored) {
        }
    }

    private static String normalizeState(String raw) {
        if (TelephonyManager.EXTRA_STATE_RINGING.equals(raw)) return "ringing";
        if (TelephonyManager.EXTRA_STATE_OFFHOOK.equals(raw)) return "offhook";
        if (TelephonyManager.EXTRA_STATE_IDLE.equals(raw)) return "idle";
        return raw.toLowerCase();
    }

    private static String lookupContactName(Context context, String number) {
        if (number == null || number.trim().isEmpty()) return "";

        Uri uri = Uri.withAppendedPath(
                ContactsContract.PhoneLookup.CONTENT_FILTER_URI,
                Uri.encode(number)
        );

        String[] projection = {
                ContactsContract.PhoneLookup.DISPLAY_NAME
        };

        try (Cursor cursor = context.getContentResolver().query(
                uri,
                projection,
                null,
                null,
                null
        )) {
            if (cursor != null && cursor.moveToFirst()) {
                String name = cursor.getString(0);
                return name == null ? "" : name;
            }
        } catch (Exception ignored) {
        }

        return "";
    }
}
