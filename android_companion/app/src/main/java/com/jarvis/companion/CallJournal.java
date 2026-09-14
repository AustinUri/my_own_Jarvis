package com.jarvis.companion;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

public final class CallJournal {
    private static final String PREFS = "jarvis_call_journal";
    private static final String KEY = "rows";
    private CallJournal() {}

    public static synchronized void record(Context context, String name, String number) {
        try {
            SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            JSONArray old = new JSONArray(prefs.getString(KEY, "[]"));
            JSONArray next = new JSONArray();
            JSONObject row = new JSONObject();
            long now = System.currentTimeMillis();
            row.put("id", "jarvis-" + now);
            row.put("name", name == null || name.trim().isEmpty() ? "Unknown" : name);
            row.put("number", PhoneNumbers.displayIsraelLocal(number));
            row.put("canonical_number", PhoneNumbers.canonical(number));
            row.put("type", "outgoing");
            row.put("type_code", 2);
            row.put("date_ms", now);
            row.put("duration_seconds", 0);
            row.put("summary_available", false);
            row.put("source", "jarvis");
            next.put(row);
            for (int i = 0; i < old.length() && i < 99; i++) next.put(old.get(i));
            prefs.edit().putString(KEY, next.toString()).apply();
        } catch (Exception ignored) {}
    }

    public static synchronized JSONArray recent(Context context, int limit) {
        JSONArray out = new JSONArray();
        try {
            JSONArray rows = new JSONArray(context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY, "[]"));
            for (int i = 0; i < rows.length() && i < limit; i++) out.put(rows.get(i));
        } catch (Exception ignored) {}
        return out;
    }
}
