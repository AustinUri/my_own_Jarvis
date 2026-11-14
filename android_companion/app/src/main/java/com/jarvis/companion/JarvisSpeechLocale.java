package com.jarvis.companion;

import android.speech.tts.TextToSpeech;
import android.util.Log;

import java.util.Locale;

public final class JarvisSpeechLocale {

    private static final String TAG = "JARVIS_TTS";

    private JarvisSpeechLocale() {
    }

    public static boolean containsHebrew(
            CharSequence value
    ) {
        if (value == null || value.length() == 0) {
            return false;
        }

        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);

            if ((c >= '\u0590' && c <= '\u05FF')
                    || (c >= '\uFB1D' && c <= '\uFB4F')) {
                return true;
            }
        }

        return false;
    }

    public static boolean applyToTts(
            TextToSpeech tts,
            String speech
    ) {
        if (tts == null) {
            return false;
        }

        boolean hebrew = containsHebrew(speech);

        Locale desired = hebrew
                ? Locale.forLanguageTag("he-IL")
                : Locale.ENGLISH;

        int result = tts.setLanguage(desired);

        if (isSupported(result)) {
            Log.d(
                    TAG,
                    "TTS locale="
                            + desired.toLanguageTag()
            );
            return true;
        }

        if (hebrew) {
            Locale plainHebrew =
                    Locale.forLanguageTag("he");

            result =
                    tts.setLanguage(
                            plainHebrew
                    );

            if (isSupported(result)) {
                Log.d(
                        TAG,
                        "TTS locale="
                                + plainHebrew.toLanguageTag()
                );
                return true;
            }
        }

        Locale fallback =
                Locale.getDefault();

        result =
                tts.setLanguage(
                        fallback
                );

        Log.w(
                TAG,
                "Requested TTS language unavailable; fallback="
                        + fallback.toLanguageTag()
                        + " result="
                        + result
        );

        return isSupported(result);
    }

    private static boolean isSupported(
            int result
    ) {
        return result != TextToSpeech.LANG_MISSING_DATA
                && result != TextToSpeech.LANG_NOT_SUPPORTED;
    }
}
