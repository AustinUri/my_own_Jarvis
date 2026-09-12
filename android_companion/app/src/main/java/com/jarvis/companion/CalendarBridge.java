package com.jarvis.companion;

import android.Manifest;
import android.content.ContentUris;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.provider.CalendarContract;

import org.json.JSONArray;
import org.json.JSONObject;

import java.time.Instant;

public final class CalendarBridge {
    private CalendarBridge() {}

    public static JSONArray upcoming(Context context, int days) throws Exception {
        if (context.checkSelfPermission(Manifest.permission.READ_CALENDAR) != PackageManager.PERMISSION_GRANTED) {
            throw new SecurityException("Calendar permission is not granted on the phone.");
        }
        int safeDays = Math.max(1, Math.min(30, days));
        long begin = System.currentTimeMillis() - 60_000L;
        long end = begin + safeDays * 24L * 60L * 60L * 1000L;
        android.net.Uri.Builder builder = CalendarContract.Instances.CONTENT_URI.buildUpon();
        ContentUris.appendId(builder, begin);
        ContentUris.appendId(builder, end);
        String[] projection = {
                CalendarContract.Instances.EVENT_ID,
                CalendarContract.Instances.TITLE,
                CalendarContract.Instances.BEGIN,
                CalendarContract.Instances.END,
                CalendarContract.Instances.EVENT_LOCATION,
                CalendarContract.Instances.CALENDAR_DISPLAY_NAME,
                CalendarContract.Instances.ALL_DAY
        };
        JSONArray out = new JSONArray();
        try (Cursor c = context.getContentResolver().query(
                builder.build(), projection, null, null, CalendarContract.Instances.BEGIN + " ASC")) {
            if (c == null) return out;
            int count = 0;
            while (c.moveToNext() && count < 80) {
                JSONObject event = new JSONObject();
                event.put("id", c.getLong(0));
                event.put("summary", safe(c.getString(1), "(No title)"));
                event.put("start", Instant.ofEpochMilli(c.getLong(2)).toString());
                event.put("end", Instant.ofEpochMilli(c.getLong(3)).toString());
                event.put("location", safe(c.getString(4), ""));
                event.put("calendar", safe(c.getString(5), ""));
                event.put("all_day", c.getInt(6) != 0);
                event.put("source", "phone");
                out.put(event);
                count++;
            }
        }
        return out;
    }

    private static String safe(String s, String fallback) { return s == null ? fallback : s; }
}
