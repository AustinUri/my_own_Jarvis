package com.jarvis.companion;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.telecom.TelecomManager;
import android.provider.ContactsContract;
import android.telephony.PhoneNumberUtils;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

public final class ContactsBridge {
    private ContactsBridge() {}

    public static JSONArray search(Context context, String query) throws Exception {
        if (context.checkSelfPermission(Manifest.permission.READ_CONTACTS) != PackageManager.PERMISSION_GRANTED) {
            throw new SecurityException("Contacts permission is not granted on the phone.");
        }
        String q = query == null ? "" : query.trim();
        if (q.isEmpty()) throw new IllegalArgumentException("Contact search is empty.");

        Map<String, JSONObject> unique = new LinkedHashMap<>();
        String[] projection = {
                ContactsContract.CommonDataKinds.Phone.CONTACT_ID,
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                ContactsContract.CommonDataKinds.Phone.NUMBER,
                ContactsContract.CommonDataKinds.Phone.TYPE,
                ContactsContract.CommonDataKinds.Phone.NORMALIZED_NUMBER
        };
        String selection = ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " LIKE ?";
        String[] args = new String[]{"%" + q.replace("%", "") + "%"};
        try (Cursor c = context.getContentResolver().query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                projection,
                selection,
                args,
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " ASC")) {
            if (c == null) return new JSONArray();
            while (c.moveToNext() && unique.size() < 24) {
                long contactId = c.getLong(0);
                String name = c.getString(1);
                String raw = c.getString(2);
                int type = c.getInt(3);
                String normalizedProvider = c.getString(4);
                if (raw == null || raw.trim().isEmpty()) continue;

                String canonical = PhoneNumbers.canonical(
                        normalizedProvider == null || normalizedProvider.trim().isEmpty() ? raw : normalizedProvider);
                String display = PhoneNumbers.displayIsraelLocal(raw);
                String safeName = name == null ? "Unknown" : name.trim();
                String key = canonical.isEmpty()
                        ? (safeName.toLowerCase(Locale.ROOT) + "|" + PhoneNumberUtils.normalizeNumber(raw))
                        : canonical;

                JSONObject row = new JSONObject();
                row.put("contact_id", contactId);
                row.put("name", safeName);
                row.put("number", display);
                row.put("raw_number", raw);
                row.put("canonical_number", canonical);
                row.put("type", type);

                JSONObject previous = unique.get(key);
                // If Android exposes the same underlying number through Google/Samsung/raw-contact
                // rows, keep one. Prefer the mobile-labelled row when duplicate metadata differs.
                if (previous == null || (type == ContactsContract.CommonDataKinds.Phone.TYPE_MOBILE
                        && previous.optInt("type", -1) != ContactsContract.CommonDataKinds.Phone.TYPE_MOBILE)) {
                    unique.put(key, row);
                }
            }
        }

        JSONArray out = new JSONArray();
        int count = 0;
        for (JSONObject row : unique.values()) {
            out.put(row);
            if (++count >= 12) break;
        }
        return out;
    }

    public static JSONObject call(Context context, String rawNumber, String name) throws Exception {
        if (context.checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED) {
            throw new SecurityException("Phone-call permission is not granted on the phone.");
        }
        String number = PhoneNumbers.displayIsraelLocal(rawNumber);
        if (number.isEmpty()) throw new IllegalArgumentException("Phone number is empty.");
        String digitsOnly = number.replaceAll("[^0-9]", "");
        String[] emergencyNumbers = {"112", "911", "999", "000", "100", "101", "102", "110", "118", "119"};
        for (String emergency : emergencyNumbers) {
            if (digitsOnly.equals(emergency)) {
                throw new SecurityException("JARVIS will not automate emergency-number calls.");
            }
        }
        if (PhoneNumberUtils.isEmergencyNumber(number)) {
            throw new SecurityException("JARVIS will not automate emergency-number calls.");
        }
        TelecomManager telecom = (TelecomManager) context.getSystemService(Context.TELECOM_SERVICE);
        if (telecom == null) throw new IllegalStateException("Android Telecom service is unavailable.");
        telecom.placeCall(Uri.parse("tel:" + Uri.encode(number)), new Bundle());
        CallJournal.record(context, name, number);
        JSONObject out = new JSONObject();
        out.put("ok", true);
        out.put("mode", "cellular-handoff");
        out.put("number", number);
        out.put("canonical_number", PhoneNumbers.canonical(number));
        out.put("name", name == null ? "" : name);
        out.put("message", "Call started on the phone. V29.1 hands the live SIM call to the user.");
        return out;
    }
}
