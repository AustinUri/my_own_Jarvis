package com.jarvis.companion;

import android.app.Notification;
import android.app.Person;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.ContactsContract;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import java.util.ArrayList;
import java.util.Locale;

public final class WhatsAppCallListenerService
        extends NotificationListenerService {

    private static final class CallerInfo {
        final String name;
        final String phone;
        final boolean fromContacts;

        CallerInfo(
                String name,
                String phone,
                boolean fromContacts
        ) {
            this.name = name == null ? "" : name.trim();
            this.phone = phone == null ? "" : phone.trim();
            this.fromContacts = fromContacts;
        }
    }


    @Override
    public void onNotificationPosted(
            StatusBarNotification sbn
    ) {

        if (!isWhatsAppNotification(sbn)) {
            return;
        }

        Notification notification =
                sbn.getNotification();

        if (!looksLikeIncomingCall(notification)) {
            return;
        }

        CallerInfo caller =
                resolveCaller(notification.extras);

        // Wait until WhatsApp actually exposes useful
        // caller/profile information.
        if (caller.name.isEmpty()) {
            return;
        }

        sendCallState(
                "ringing",
                caller
        );
    }


    @Override
    public void onNotificationRemoved(
            StatusBarNotification sbn
    ) {

        if (!isWhatsAppNotification(sbn)) {
            return;
        }

        Notification notification =
                sbn.getNotification();

        if (!looksLikeIncomingCall(notification)) {
            return;
        }

        CallerInfo caller =
                resolveCaller(notification.extras);

        sendCallState(
                "idle",
                caller
        );
    }


    private boolean isWhatsAppNotification(
            StatusBarNotification sbn
    ) {

        if (sbn == null
                || sbn.getNotification() == null) {
            return false;
        }

        String pkg = sbn.getPackageName();

        return "com.whatsapp".equals(pkg)
                || "com.whatsapp.w4b".equals(pkg);
    }


    private boolean looksLikeIncomingCall(
            Notification notification
    ) {

        if (notification == null) {
            return false;
        }

        if (Notification.CATEGORY_CALL.equals(
                notification.category
        )) {
            return true;
        }

        Bundle extras = notification.extras;

        String text =
                (
                        value(
                                extras,
                                Notification.EXTRA_TITLE
                        )
                                + " "
                                + value(
                                extras,
                                Notification.EXTRA_TEXT
                        )
                                + " "
                                + value(
                                extras,
                                Notification.EXTRA_SUB_TEXT
                        )
                ).toLowerCase(Locale.ROOT);

        return (
                text.contains("incoming")
                        && (
                        text.contains("call")
                                || text.contains("voice")
                                || text.contains("video")
                )
        )
                || text.contains("\u05e9\u05d9\u05d7\u05d4 \u05e0\u05db\u05e0\u05e1\u05ea")
                || text.contains("\u05e9\u05d9\u05d7\u05ea \u05e7\u05d5\u05dc")
                || text.contains("\u05e9\u05d9\u05d7\u05ea \u05d5\u05d9\u05d3\u05d0\u05d5");
    }


    private CallerInfo resolveCaller(
            Bundle extras
    ) {

        String whatsappProfileName =
                extractWhatsAppName(extras);

        String discoveredPhone = "";

        /*
         * Priority 1:
         * WhatsApp notification Person metadata.
         *
         * If it points to a phone/contact already stored
         * on the Samsung, use the Samsung Contacts name.
         */
        if (extras != null) {

            Object people =
                    extras.get(
                            Notification.EXTRA_PEOPLE_LIST
                    );

            if (people instanceof ArrayList<?>) {

                for (Object item :
                        (ArrayList<?>) people) {

                    if (!(item instanceof Person)) {
                        continue;
                    }

                    Person person = (Person) item;

                    String personName =
                            clean(
                                    person.getName() == null
                                            ? ""
                                            : person.getName().toString()
                            );

                    if (whatsappProfileName.isEmpty()
                            && isUsefulName(personName)) {
                        whatsappProfileName =
                                personName;
                    }

                    String rawUri =
                            clean(person.getUri());

                    CallerInfo contact =
                            resolvePersonUri(
                                    rawUri
                            );

                    if (contact != null) {

                        if (!contact.phone.isEmpty()) {
                            discoveredPhone =
                                    contact.phone;
                        }

                        if (contact.fromContacts
                                && !contact.name.isEmpty()) {

                            return contact;
                        }
                    }
                }
            }


            /*
             * Older/legacy people metadata.
             */
            Object legacy =
                    extras.get(
                            Notification.EXTRA_PEOPLE
                    );

            if (legacy instanceof Object[]) {

                for (Object item :
                        (Object[]) legacy) {

                    if (item == null) {
                        continue;
                    }

                    CallerInfo contact =
                            resolvePersonUri(
                                    item.toString()
                            );

                    if (contact != null) {

                        if (!contact.phone.isEmpty()) {
                            discoveredPhone =
                                    contact.phone;
                        }

                        if (contact.fromContacts
                                && !contact.name.isEmpty()) {

                            return contact;
                        }
                    }
                }
            }
        }


        /*
         * Priority 2:
         * Not found in Samsung Contacts.
         * Use the identity/profile label exposed by WhatsApp.
         */
        return new CallerInfo(
                whatsappProfileName,
                discoveredPhone,
                false
        );
    }


    private CallerInfo resolvePersonUri(
            String raw
    ) {

        raw = clean(raw);

        if (raw.isEmpty()) {
            return null;
        }

        try {
            Uri uri = Uri.parse(raw);

            if ("tel".equalsIgnoreCase(
                    uri.getScheme()
            )) {

                String number =
                        clean(
                                uri.getSchemeSpecificPart()
                        );

                String contactName =
                        lookupContactByNumber(
                                number
                        );

                if (!contactName.isEmpty()) {
                    return new CallerInfo(
                            contactName,
                            number,
                            true
                    );
                }

                return new CallerInfo(
                        "",
                        number,
                        false
                );
            }


            if ("content".equalsIgnoreCase(
                    uri.getScheme()
            )) {

                String contactName =
                        lookupContactByUri(
                                uri
                        );

                if (!contactName.isEmpty()) {
                    return new CallerInfo(
                            contactName,
                            "",
                            true
                    );
                }
            }

        } catch (Exception ignored) {
        }


        if (looksLikePhoneNumber(raw)) {

            String contactName =
                    lookupContactByNumber(raw);

            if (!contactName.isEmpty()) {
                return new CallerInfo(
                        contactName,
                        raw,
                        true
                );
            }

            return new CallerInfo(
                    "",
                    raw,
                    false
            );
        }

        return null;
    }


    private String lookupContactByNumber(
            String number
    ) {

        if (number == null
                || number.trim().isEmpty()) {
            return "";
        }

        Uri uri =
                Uri.withAppendedPath(
                        ContactsContract
                                .PhoneLookup
                                .CONTENT_FILTER_URI,
                        Uri.encode(number)
                );

        String[] projection = {
                ContactsContract
                        .PhoneLookup
                        .DISPLAY_NAME
        };

        try (Cursor cursor =
                     getContentResolver().query(
                             uri,
                             projection,
                             null,
                             null,
                             null
                     )) {

            if (cursor != null
                    && cursor.moveToFirst()) {

                return clean(
                        cursor.getString(0)
                );
            }

        } catch (Exception ignored) {
        }

        return "";
    }


    private String lookupContactByUri(
            Uri uri
    ) {

        if (uri == null) {
            return "";
        }

        String[] projection = {
                ContactsContract
                        .Contacts
                        .DISPLAY_NAME_PRIMARY
        };

        try (Cursor cursor =
                     getContentResolver().query(
                             uri,
                             projection,
                             null,
                             null,
                             null
                     )) {

            if (cursor != null
                    && cursor.moveToFirst()) {

                return clean(
                        cursor.getString(0)
                );
            }

        } catch (Exception ignored) {
        }

        return "";
    }


    private String extractWhatsAppName(
            Bundle extras
    ) {

        String title =
                clean(
                        value(
                                extras,
                                Notification.EXTRA_TITLE
                        )
                );

        if (isUsefulName(title)) {
            return title;
        }


        String conversation =
                clean(
                        value(
                                extras,
                                Notification
                                        .EXTRA_CONVERSATION_TITLE
                        )
                );

        if (isUsefulName(conversation)) {
            return conversation;
        }


        if (extras != null) {

            Object people =
                    extras.get(
                            Notification.EXTRA_PEOPLE_LIST
                    );

            if (people instanceof ArrayList<?>) {

                for (Object item :
                        (ArrayList<?>) people) {

                    if (!(item instanceof Person)) {
                        continue;
                    }

                    Person person =
                            (Person) item;

                    String name =
                            clean(
                                    person.getName() == null
                                            ? ""
                                            : person.getName()
                                            .toString()
                            );

                    if (isUsefulName(name)) {
                        return name;
                    }
                }
            }
        }

        return "";
    }


    private boolean isUsefulName(
            String value
    ) {

        value = clean(value);

        if (value.isEmpty()) {
            return false;
        }

        String lower =
                value.toLowerCase(
                        Locale.ROOT
                );

        if ("whatsapp".equals(lower)
                || "whatsapp business".equals(lower)) {
            return false;
        }

        return !lower.equals("incoming call")
                && !lower.equals("incoming voice call")
                && !lower.equals("incoming video call")
                && !lower.equals("voice call")
                && !lower.equals("video call")
                && !lower.equals("???? ?????")
                && !lower.equals("???? ???")
                && !lower.equals("???? ?????");
    }


    private void sendCallState(
            String state,
            CallerInfo caller
    ) {

        try {
            Intent intent =
                    new Intent(
                            this,
                            JarvisForegroundService.class
                    );

            intent.setAction(
                    JarvisForegroundService
                            .ACTION_WHATSAPP_CALL_EVENT
            );

            intent.putExtra(
                    "call_state",
                    state
            );

            intent.putExtra(
                    "call_direction",
                    "incoming"
            );

            intent.putExtra(
                    "call_number",
                    caller == null
                            ? ""
                            : caller.phone
            );

            intent.putExtra(
                    "caller_name",
                    caller == null
                            ? ""
                            : caller.name
            );

            intent.putExtra(
                    "occurred_at_ms",
                    System.currentTimeMillis()
            );

            if (Build.VERSION.SDK_INT
                    >= Build.VERSION_CODES.O) {

                startForegroundService(intent);

            } else {

                startService(intent);
            }

        } catch (Exception ignored) {
        }
    }


    private static String value(
            Bundle extras,
            String key
    ) {

        if (extras == null) {
            return "";
        }

        CharSequence value =
                extras.getCharSequence(key);

        return value == null
                ? ""
                : value.toString();
    }


    private static String clean(
            String value
    ) {

        return value == null
                ? ""
                : value.trim();
    }


    private static boolean looksLikePhoneNumber(
            String value
    ) {

        if (value == null) {
            return false;
        }

        int digits = 0;

        for (int i = 0;
             i < value.length();
             i++) {

            if (Character.isDigit(
                    value.charAt(i)
            )) {
                digits++;
            }
        }

        return digits >= 7;
    }
}
