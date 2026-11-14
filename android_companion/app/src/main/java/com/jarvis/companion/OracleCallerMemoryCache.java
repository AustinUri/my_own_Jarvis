package com.jarvis.companion;

import android.content.Context;
import android.content.SharedPreferences;

public final class OracleCallerMemoryCache {
    private static final String PREFS =
            "jarvis_oracle_caller_memory_v1";
    private static final String NAME_PREFIX = "name:";
    private static final String SOURCE_PREFIX = "source:";
    private static final String PROVIDER_PREFIX = "provider:";

    private OracleCallerMemoryCache() {}

    public static void remember(
            Context context,
            String rawNumber,
            String displayName,
            String source,
            String provider
    ) {
        if (context == null) return;

        String name = clean(displayName);
        if (name.isEmpty()) return;

        String safeSource = clean(source);
        String safeProvider = clean(provider);

        // Defense in depth: only identities explicitly learned/owned by JARVIS
        // are persisted on the phone. Unknown external/provider guesses are not.
        boolean trusted =
                "user_confirmed".equalsIgnoreCase(safeSource)
                        || "jarvis_local".equalsIgnoreCase(safeProvider);

        if (!trusted) return;

        String key = keyFor(rawNumber);
        if (key.isEmpty()) return;

        SharedPreferences prefs = context.getSharedPreferences(
                PREFS,
                Context.MODE_PRIVATE
        );

        prefs.edit()
                .putString(NAME_PREFIX + key, name)
                .putString(SOURCE_PREFIX + key, safeSource)
                .putString(PROVIDER_PREFIX + key, safeProvider)
                .apply();
    }

    public static String lookupName(
            Context context,
            String rawNumber
    ) {
        if (context == null) return "";

        String key = keyFor(rawNumber);
        if (key.isEmpty()) return "";

        SharedPreferences prefs = context.getSharedPreferences(
                PREFS,
                Context.MODE_PRIVATE
        );

        return clean(
                prefs.getString(NAME_PREFIX + key, "")
        );
    }

    static String keyFor(String rawNumber) {
        String raw = clean(rawNumber);
        if (raw.isEmpty()) return "";

        try {
            String canonical = PhoneNumbers.canonical(raw);
            if (canonical != null) {
                canonical = canonical.trim();
                if (!canonical.isEmpty()) {
                    return canonical;
                }
            }
        } catch (Exception ignored) {
        }

        StringBuilder digits = new StringBuilder();
        for (int i = 0; i < raw.length(); i++) {
            char c = raw.charAt(i);
            if (Character.isDigit(c)) {
                digits.append(c);
            }
        }

        return digits.toString();
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
