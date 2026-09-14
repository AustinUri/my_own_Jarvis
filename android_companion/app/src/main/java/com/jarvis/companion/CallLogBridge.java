package com.jarvis.companion;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.provider.CallLog;

import org.json.JSONArray;
import org.json.JSONObject;

public final class CallLogBridge {
    private CallLogBridge() {}

    public static JSONArray recent(Context context, int requestedLimit) throws Exception {
        if (context.checkSelfPermission(Manifest.permission.READ_CALL_LOG) != PackageManager.PERMISSION_GRANTED) {
            return CallJournal.recent(context, Math.max(1, Math.min(100, requestedLimit)));
        }
        int limit = Math.max(1, Math.min(100, requestedLimit));
        JSONArray out = new JSONArray();
        String[] projection = {
                CallLog.Calls._ID,
                CallLog.Calls.CACHED_NAME,
                CallLog.Calls.NUMBER,
                CallLog.Calls.TYPE,
                CallLog.Calls.DATE,
                CallLog.Calls.DURATION
        };
        try (Cursor c = context.getContentResolver().query(
                CallLog.Calls.CONTENT_URI,
                projection,
                null,
                null,
                CallLog.Calls.DATE + " DESC")) {
            if (c == null) return out;
            int count = 0;
            while (c.moveToNext() && count < limit) {
                long id = c.getLong(0);
                String name = c.getString(1);
                String raw = c.getString(2);
                int type = c.getInt(3);
                long date = c.getLong(4);
                long duration = c.getLong(5);
                JSONObject row = new JSONObject();
                row.put("id", id);
                row.put("name", name == null || name.trim().isEmpty() ? "Unknown" : name);
                row.put("number", PhoneNumbers.displayIsraelLocal(raw));
                row.put("canonical_number", PhoneNumbers.canonical(raw));
                row.put("type", typeName(type));
                row.put("type_code", type);
                row.put("date_ms", date);
                row.put("duration_seconds", duration);
                row.put("summary_available", false);
                out.put(row);
                count++;
            }
        }
        return out;
    }

    public static boolean hasFullAccess(Context context) {
        return context.checkSelfPermission(Manifest.permission.READ_CALL_LOG) == PackageManager.PERMISSION_GRANTED;
    }

    private static String typeName(int type) {
        if (type == CallLog.Calls.INCOMING_TYPE) return "incoming";
        if (type == CallLog.Calls.OUTGOING_TYPE) return "outgoing";
        if (type == CallLog.Calls.MISSED_TYPE) return "missed";
        if (type == CallLog.Calls.REJECTED_TYPE) return "rejected";
        if (type == CallLog.Calls.BLOCKED_TYPE) return "blocked";
        if (type == CallLog.Calls.VOICEMAIL_TYPE) return "voicemail";
        return "other";
    }
}
