package com.jarvis.companion;

import android.Manifest;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.media.AudioManager;
import android.speech.tts.TextToSpeech;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public final class UnlockCallBriefing {
    private static final String PREF_INITIALIZED =
            "jarvis_unlock_call_briefing_initialized";
    private static final String PREF_LAST_SCAN_MS =
            "jarvis_unlock_call_briefing_last_scan_ms";

    private static final Object TTS_LOCK = new Object();
    private static TextToSpeech tts;
    private static boolean ttsReady = false;
    private static String pendingSpeech = "";

    private UnlockCallBriefing() {}

    public static void initializeBaseline(Context context) {
        if (context == null) return;

        SharedPreferences prefs = context.getSharedPreferences(
                PhoneApiClient.PREFS,
                Context.MODE_PRIVATE
        );

        if (!prefs.getBoolean(PREF_INITIALIZED, false)) {
            prefs.edit()
                    .putBoolean(PREF_INITIALIZED, true)
                    .putLong(PREF_LAST_SCAN_MS, System.currentTimeMillis())
                    .apply();
        }
    }

    public static void onUserPresent(Context context) {
        if (context == null) return;

        Context appContext = context.getApplicationContext();

        new Thread(
                () -> checkAndSpeak(appContext),
                "jarvis-unlock-call-briefing"
        ).start();
    }

    private static void checkAndSpeak(Context context) {
        try {
            if (context.checkSelfPermission(Manifest.permission.READ_CALL_LOG)
                    != PackageManager.PERMISSION_GRANTED) {
                return;
            }

            if (!shouldSpeakNow(context)) {
                return;
            }

            SharedPreferences prefs = context.getSharedPreferences(
                    PhoneApiClient.PREFS,
                    Context.MODE_PRIVATE
            );

            long lastScan = prefs.getLong(
                    PREF_LAST_SCAN_MS,
                    System.currentTimeMillis()
            );
            long now = System.currentTimeMillis();

            JSONArray calls = CallLogBridge.recent(context, 100);

            // If a later outgoing call or answered incoming call exists for the
            // same person, the earlier missed call has already been handled.
            Map<String, Long> handledAfter = new HashMap<>();

            for (int i = 0; i < calls.length(); i++) {
                JSONObject row = calls.optJSONObject(i);
                if (row == null) continue;

                String key = callerKey(row);
                if (key.isEmpty()) continue;

                String type = row.optString("type", "");
                long date = row.optLong("date_ms", 0L);
                long duration = row.optLong("duration_seconds", 0L);

                boolean handled =
                        "outgoing".equals(type)
                                || ("incoming".equals(type) && duration > 0L);

                if (handled) {
                    Long previous = handledAfter.get(key);
                    if (previous == null || date > previous) {
                        handledAfter.put(key, date);
                    }
                }
            }

            LinkedHashMap<String, MissedGroup> groups =
                    new LinkedHashMap<>();

            for (int i = 0; i < calls.length(); i++) {
                JSONObject row = calls.optJSONObject(i);
                if (row == null) continue;

                if (!"missed".equals(row.optString("type", ""))) {
                    continue;
                }

                long date = row.optLong("date_ms", 0L);

                if (date <= lastScan || date > now + 60_000L) {
                    continue;
                }

                String key = callerKey(row);
                if (key.isEmpty()) {
                    key = "unknown:" + date;
                }

                Long handledAt = handledAfter.get(key);
                if (handledAt != null && handledAt > date) {
                    continue;
                }

                String number =
                        row.optString(
                                "canonical_number",
                                row.optString("number", "")
                        ).trim();

                String name =
                        safeAndroidName(
                                row.optString("name", "")
                        );

                // Priority:
                // 1) Android Contacts / CallLog cached contact name.
                // 2) JARVIS identity learned in Oracle and cached locally when
                //    caller_intelligence_result arrived during ringing.
                // 3) Unknown.
                if (name.isEmpty()) {
                    name = OracleCallerMemoryCache.lookupName(
                            context,
                            number
                    );
                }

                MissedGroup group = groups.get(key);

                if (group == null) {
                    group = new MissedGroup(
                            name,
                            number,
                            date
                    );

                    groups.put(key, group);

                } else {
                    group.count++;

                    if (date > group.latestDateMs) {
                        group.latestDateMs = date;
                    }

                    // Prefer a newly resolved identity if the first row was
                    // unknown.
                    if (group.name.isEmpty() && !name.isEmpty()) {
                        group.name = name;
                    }
                }
            }

            // Advance checkpoint even if nothing is worth announcing.
            if (groups.isEmpty()) {
                prefs.edit()
                        .putLong(PREF_LAST_SCAN_MS, now)
                        .apply();
                return;
            }

            String speech = buildHebrewSpeech(groups);

            if (speech.isEmpty()) {
                prefs.edit()
                        .putLong(PREF_LAST_SCAN_MS, now)
                        .apply();
                return;
            }

            // Mark as briefed BEFORE speech. Re-lock/re-unlock must not repeat.
            prefs.edit()
                    .putLong(PREF_LAST_SCAN_MS, now)
                    .apply();

            speakHebrew(context, speech);

        } catch (Exception ignored) {
            // This is a convenience feature. Never destabilize the dialer.
        }
    }

    private static boolean shouldSpeakNow(Context context) {
        try {
            AudioManager audio =
                    (AudioManager) context.getSystemService(
                            Context.AUDIO_SERVICE
                    );

            if (audio == null) return true;

            return audio.getRingerMode()
                    == AudioManager.RINGER_MODE_NORMAL;

        } catch (Exception ignored) {
            return true;
        }
    }

    private static String callerKey(JSONObject row) {
        String canonical =
                row.optString(
                        "canonical_number",
                        ""
                ).trim();

        if (!canonical.isEmpty()) {
            return canonical;
        }

        return OracleCallerMemoryCache.keyFor(
                row.optString("number", "")
        );
    }

    private static String safeAndroidName(String raw) {
        String value = raw == null ? "" : raw.trim();

        if (value.isEmpty()
                || "unknown".equalsIgnoreCase(value)
                || "private".equalsIgnoreCase(value)
                || "anonymous".equalsIgnoreCase(value)) {
            return "";
        }

        return value;
    }

    private static String buildHebrewSpeech(
            LinkedHashMap<String, MissedGroup> groups
    ) {
        List<MissedGroup> items =
                new ArrayList<>(groups.values());

        int totalCalls = 0;
        for (MissedGroup group : items) {
            totalCalls += group.count;
        }

        if (items.size() == 1) {
            MissedGroup only = items.get(0);
            String who = displayWho(only);

            if (only.count == 1) {
                return "אורי, בזמן שלא היית בטלפון פספסת שיחה מ"
                        + who
                        + ", בשעה "
                        + formatTime(only.latestDateMs)
                        + ".";
            }

            return "אורי, בזמן שלא היית בטלפון "
                    + who
                    + " התקשר אליך "
                    + hebrewCount(only.count)
                    + ".";
        }

        StringBuilder speech = new StringBuilder();

        speech.append(
                "אורי, בזמן שלא היית בטלפון היו לך "
        )
                .append(totalCalls)
                .append(" שיחות שלא נענו. ");

        int announced = 0;

        for (MissedGroup group : items) {
            if (announced >= 4) break;

            if (announced > 0) {
                speech.append(", ");
            }

            speech.append(displayWho(group));

            if (group.count > 1) {
                speech.append(" התקשר ")
                        .append(
                                hebrewCount(group.count)
                        );
            } else {
                speech.append(" התקשר פעם אחת");
            }

            announced++;
        }

        int remaining =
                items.size() - announced;

        if (remaining > 0) {
            speech.append(", ועוד ")
                    .append(remaining)
                    .append(" מתקשרים");
        }

        speech.append(".");

        return speech.toString();
    }

    private static String displayWho(
            MissedGroup group
    ) {
        if (group.name != null
                && !group.name.isEmpty()) {
            return group.name;
        }

        return "מספר לא מוכר";
    }

    private static String formatTime(long dateMs) {
        try {
            return new SimpleDateFormat(
                    "HH:mm",
                    new Locale("he", "IL")
            ).format(dateMs);

        } catch (Exception ignored) {
            return "";
        }
    }

    private static String hebrewCount(int count) {
        switch (count) {
            case 2:
                return "פעמיים";
            case 3:
                return "שלוש פעמים";
            case 4:
                return "ארבע פעמים";
            case 5:
                return "חמש פעמים";
            default:
                return count + " פעמים";
        }
    }

    private static void speakHebrew(
            Context context,
            String speech
    ) {
        if (speech == null
                || speech.trim().isEmpty()) {
            return;
        }

        synchronized (TTS_LOCK) {
            pendingSpeech = speech.trim();

            if (tts == null) {
                ttsReady = false;

                tts = new TextToSpeech(
                        context.getApplicationContext(),
                        status -> {
                            synchronized (TTS_LOCK) {
                                if (status
                                        == TextToSpeech.SUCCESS) {

                                    int result =
                                            tts.setLanguage(
                                                    new Locale(
                                                            "he",
                                                            "IL"
                                                    )
                                            );

                                    ttsReady =
                                            result
                                                    != TextToSpeech.LANG_MISSING_DATA
                                                    && result
                                                    != TextToSpeech.LANG_NOT_SUPPORTED;

                                    if (!ttsReady) {
                                        tts.setLanguage(
                                                Locale.getDefault()
                                        );
                                        ttsReady = true;
                                    }

                                    speakPendingLocked();
                                }
                            }
                        }
                );

                return;
            }

            if (ttsReady) {
                speakPendingLocked();
            }
        }
    }

    private static void speakPendingLocked() {
        if (tts == null || !ttsReady) return;

        if (pendingSpeech == null
                || pendingSpeech.isEmpty()) {
            return;
        }

        String speech = pendingSpeech;
        pendingSpeech = "";

        tts.speak(
                speech,
                TextToSpeech.QUEUE_FLUSH,
                null,
                "jarvis-unlock-call-briefing"
        );
    }

    public static void shutdown() {
        synchronized (TTS_LOCK) {
            if (tts != null) {
                try {
                    tts.stop();
                    tts.shutdown();
                } catch (Exception ignored) {
                }
            }

            tts = null;
            ttsReady = false;
            pendingSpeech = "";
        }
    }

    private static final class MissedGroup {
        String name;
        final String number;
        int count = 1;
        long latestDateMs;

        MissedGroup(
                String name,
                String number,
                long latestDateMs
        ) {
            this.name =
                    name == null ? "" : name;
            this.number =
                    number == null ? "" : number;
            this.latestDateMs =
                    latestDateMs;
        }
    }
}
