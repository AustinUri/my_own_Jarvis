package com.jarvis.companion;

import android.content.ContentResolver;
import android.content.Context;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.provider.ContactsContract;
import android.telephony.PhoneNumberUtils;

import java.io.InputStream;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public final class JarvisCallerIdentity {

    public static final class Result {
        public final String displayName;
        public final String number;
        public final Bitmap photo;
        public final String source;

        Result(
                String displayName,
                String number,
                Bitmap photo,
                String source
        ) {
            this.displayName = safe(displayName);
            this.number = safe(number);
            this.photo = photo;
            this.source = safe(source);
        }
    }

    private static final class ExternalIdentity {
        final String displayName;

        ExternalIdentity(String displayName) {
            this.displayName = safe(displayName);
        }
    }

    private static final Map<String, ExternalIdentity> EXTERNAL =
            new ConcurrentHashMap<>();

    private JarvisCallerIdentity() {
    }

    public static void rememberExternalIdentity(
            String number,
            String displayName
    ) {
        String key = normalize(number);
        String name = safe(displayName);

        if (key.isEmpty() || name.isEmpty()) {
            return;
        }

        EXTERNAL.put(
                key,
                new ExternalIdentity(name)
        );
    }

    public static Result resolve(
            Context context,
            String number,
            String telecomDisplayName
    ) {
        String cleanNumber = safe(number);

        Result contact =
                lookupContact(
                        context,
                        cleanNumber
                );

        if (!contact.displayName.isEmpty()) {
            return contact;
        }

        String telecomName =
                safe(telecomDisplayName);

        if (!telecomName.isEmpty()) {
            return new Result(
                    telecomName,
                    cleanNumber,
                    null,
                    "telecom"
            );
        }

        ExternalIdentity external =
                EXTERNAL.get(
                        normalize(cleanNumber)
                );

        if (external != null
                && !external.displayName.isEmpty()) {
            return new Result(
                    external.displayName,
                    cleanNumber,
                    null,
                    "jarvis_oracle"
            );
        }

        return new Result(
                cleanNumber.isEmpty()
                        ? "Unknown caller"
                        : cleanNumber,
                cleanNumber,
                null,
                "number"
        );
    }

    public static Bitmap loadPhoto(
            Context context,
            String uriText
    ) {
        if (context == null
                || safe(uriText).isEmpty()) {
            return null;
        }

        return loadPhoto(
                context.getContentResolver(),
                uriText
        );
    }

    public static String normalize(
            String number
    ) {
        String raw = safe(number);

        if (raw.isEmpty()) {
            return "";
        }

        String normalized =
                PhoneNumberUtils.normalizeNumber(
                        raw
                );

        if (normalized == null) {
            normalized = "";
        }

        normalized =
                normalized.replace("+", "");

        if (normalized.startsWith("972")
                && normalized.length() >= 11) {
            normalized =
                    "0"
                            + normalized.substring(3);
        }

        return normalized;
    }

    public static String displayNumber(
            String number
    ) {
        String raw = safe(number);

        if (raw.isEmpty()) {
            return "";
        }

        String formatted =
                PhoneNumberUtils.formatNumber(
                        raw,
                        "IL"
                );

        return formatted == null
                || formatted.trim().isEmpty()
                ? raw
                : formatted;
    }

    private static Result lookupContact(
            Context context,
            String number
    ) {
        if (context == null
                || safe(number).isEmpty()) {
            return new Result(
                    "",
                    safe(number),
                    null,
                    ""
            );
        }

        Uri uri =
                Uri.withAppendedPath(
                        ContactsContract.PhoneLookup
                                .CONTENT_FILTER_URI,
                        Uri.encode(number)
                );

        String[] projection =
                new String[]{
                        ContactsContract.PhoneLookup
                                .DISPLAY_NAME,
                        ContactsContract.PhoneLookup
                                .PHOTO_URI
                };

        try (
                Cursor cursor =
                        context.getContentResolver().query(
                                uri,
                                projection,
                                null,
                                null,
                                null
                        )
        ) {
            if (cursor == null
                    || !cursor.moveToFirst()) {
                return new Result(
                        "",
                        number,
                        null,
                        ""
                );
            }

            String name =
                    column(
                            cursor,
                            ContactsContract.PhoneLookup
                                    .DISPLAY_NAME
                    );

            String photoUri =
                    column(
                            cursor,
                            ContactsContract.PhoneLookup
                                    .PHOTO_URI
                    );

            Bitmap photo =
                    loadPhoto(
                            context.getContentResolver(),
                            photoUri
                    );

            return new Result(
                    name,
                    number,
                    photo,
                    "contacts"
            );

        } catch (SecurityException ignored) {
            return new Result(
                    "",
                    number,
                    null,
                    ""
            );
        }
    }

    private static Bitmap loadPhoto(
            ContentResolver resolver,
            String uriText
    ) {
        if (resolver == null
                || safe(uriText).isEmpty()) {
            return null;
        }

        try (
                InputStream input =
                        resolver.openInputStream(
                                Uri.parse(uriText)
                        )
        ) {
            if (input == null) {
                return null;
            }

            return BitmapFactory.decodeStream(input);

        } catch (Exception ignored) {
            return null;
        }
    }

    private static String column(
            Cursor cursor,
            String name
    ) {
        int index =
                cursor.getColumnIndex(name);

        if (index < 0
                || cursor.isNull(index)) {
            return "";
        }

        return safe(
                cursor.getString(index)
        );
    }

    private static String safe(
            String value
    ) {
        return value == null
                ? ""
                : value.trim();
    }
}
