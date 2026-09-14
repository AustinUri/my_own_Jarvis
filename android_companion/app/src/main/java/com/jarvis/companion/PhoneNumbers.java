package com.jarvis.companion;

import android.telephony.PhoneNumberUtils;

public final class PhoneNumbers {
    private PhoneNumbers() {}

    public static String canonical(String raw) {
        String value = raw == null ? "" : raw.trim();
        if (value.isEmpty()) return "";
        String normalized = PhoneNumberUtils.normalizeNumber(value);
        if (normalized == null) normalized = "";
        normalized = normalized.trim();
        if (normalized.startsWith("00972")) normalized = "+972" + normalized.substring(5);
        if (normalized.startsWith("972")) normalized = "+" + normalized;
        if (normalized.startsWith("+9720")) normalized = "+972" + normalized.substring(5);
        if (normalized.startsWith("+972")) return "+972" + normalized.substring(4).replaceFirst("^0+", "");
        if (normalized.startsWith("0") && normalized.length() >= 9) return "+972" + normalized.substring(1);
        return normalized;
    }

    public static String displayIsraelLocal(String raw) {
        String c = canonical(raw);
        if (c.startsWith("+972") && c.length() > 4) {
            return "0" + c.substring(4);
        }
        String normalized = PhoneNumberUtils.normalizeNumber(raw == null ? "" : raw);
        return normalized == null || normalized.isEmpty() ? (raw == null ? "" : raw.trim()) : normalized;
    }
}
