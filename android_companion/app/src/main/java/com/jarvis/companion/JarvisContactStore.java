package com.jarvis.companion;

import android.Manifest;
import android.content.ContentProviderOperation;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.OperationApplicationException;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.RemoteException;
import android.provider.ContactsContract;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class JarvisContactStore {

    public static final class GroupInfo {
        public final long id;
        public final String title;
        public final String accountName;
        public final String accountType;

        GroupInfo(
                long id,
                String title,
                String accountName,
                String accountType
        ) {
            this.id = id;
            this.title = safe(title);
            this.accountName = safe(accountName);
            this.accountType = safe(accountType);
        }

        public boolean matches(
                AccountInfo account
        ) {
            if (account == null) {
                return accountName.isEmpty()
                        && accountType.isEmpty();
            }

            return accountName.equals(
                    safe(account.name)
            )
                    && accountType.equals(
                    safe(account.type)
            );
        }
    }

    public static final class AccountInfo {
        public final String name;
        public final String type;

        AccountInfo(
                String name,
                String type
        ) {
            this.name = safe(name);
            this.type = safe(type);
        }

        public String label() {
            String lowerType =
                    type.toLowerCase();

            if (type.isEmpty()
                    || "vnd.sec.contact.phone".equals(
                    lowerType
            )) {
                return "Phone (device)";
            }

            if ("com.google".equals(
                    lowerType
            )) {
                return name.isEmpty()
                        ? "Google"
                        : "Google • " + name;
            }

            if (lowerType.contains("samsung")) {
                return name.isEmpty()
                        ? "Samsung account"
                        : "Samsung • " + name;
            }

            if (!name.isEmpty()) {
                return "Account • " + name;
            }

            return "Other account";
        }
    }

    public static final class PhoneData {
        public final long dataId;
        public final long rawContactId;
        public final String number;
        public final int type;
        public final String customLabel;

        PhoneData(
                long dataId,
                long rawContactId,
                String number,
                int type,
                String customLabel
        ) {
            this.dataId = dataId;
            this.rawContactId = rawContactId;
            this.number = safe(number);
            this.type = type;
            this.customLabel = safe(customLabel);
        }
    }

    public static final class ContactData {
        public final long contactId;
        public final String name;
        public final boolean starred;
        public final String photoUri;
        public final String lookupKey;
        public final long primaryRawContactId;
        public final AccountInfo account;
        public final List<PhoneData> phones;
        public final Set<Long> groupIds;

        ContactData(
                long contactId,
                String name,
                boolean starred,
                String photoUri,
                String lookupKey,
                long primaryRawContactId,
                AccountInfo account,
                List<PhoneData> phones,
                Set<Long> groupIds
        ) {
            this.contactId = contactId;
            this.name = safe(name);
            this.starred = starred;
            this.photoUri = safe(photoUri);
            this.lookupKey = safe(lookupKey);
            this.primaryRawContactId =
                    primaryRawContactId;
            this.account = account;
            this.phones = phones;
            this.groupIds = groupIds;
        }
    }

    public static final class PhoneEdit {
        public final long dataId;
        public final String number;
        public final int type;
        public final String customLabel;

        public PhoneEdit(
                long dataId,
                String number,
                int type,
                String customLabel
        ) {
            this.dataId = dataId;
            this.number = safe(number);
            this.type = type;
            this.customLabel = safe(customLabel);
        }
    }

    public static final class SaveResult {
        public final boolean ok;
        public final long contactId;
        public final String message;

        SaveResult(
                boolean ok,
                long contactId,
                String message
        ) {
            this.ok = ok;
            this.contactId = contactId;
            this.message = safe(message);
        }

        static SaveResult ok(
                long contactId
        ) {
            return new SaveResult(
                    true,
                    contactId,
                    "Saved"
            );
        }

        static SaveResult fail(
                String message
        ) {
            return new SaveResult(
                    false,
                    -1L,
                    message
            );
        }
    }

    private JarvisContactStore() {
    }

    public static boolean canWrite(
            Context context
    ) {
        return context != null
                && context.checkSelfPermission(
                Manifest.permission.WRITE_CONTACTS
        ) == PackageManager.PERMISSION_GRANTED;
    }

    public static Bitmap loadContactPhoto(
            Context context,
            long contactId,
            String fallbackUri
    ) {
        if (context == null) {
            return null;
        }

        if (contactId > 0L) {
            Uri contactUri =
                    Uri.withAppendedPath(
                            ContactsContract.Contacts
                                    .CONTENT_URI,
                            Long.toString(contactId)
                    );

            try (
                    InputStream input =
                            ContactsContract.Contacts
                                    .openContactPhotoInputStream(
                                            context.getContentResolver(),
                                            contactUri,
                                            false
                                    )
            ) {
                if (input != null) {
                    Bitmap bitmap =
                            BitmapFactory.decodeStream(
                                    input
                            );

                    if (bitmap != null) {
                        return bitmap;
                    }
                }

            } catch (Exception ignored) {
            }
        }

        return JarvisCallerIdentity.loadPhoto(
                context,
                fallbackUri
        );
    }

    public static List<GroupInfo> loadGroups(
            Context context
    ) {
        List<GroupInfo> groups =
                new ArrayList<>();

        if (context == null) {
            return groups;
        }

        Map<Long, Integer> memberCounts =
                new LinkedHashMap<>();

        Map<Long, Set<Long>> memberships =
                loadMemberships(context);

        for (Set<Long> groupIds
                : memberships.values()) {

            for (Long groupId : groupIds) {
                if (groupId == null
                        || groupId <= 0L) {
                    continue;
                }

                Integer count =
                        memberCounts.get(groupId);

                memberCounts.put(
                        groupId,
                        count == null
                                ? 1
                                : count + 1
                );
            }
        }

        String[] projection =
                new String[]{
                        ContactsContract.Groups._ID,
                        ContactsContract.Groups.TITLE,
                        ContactsContract.Groups.ACCOUNT_NAME,
                        ContactsContract.Groups.ACCOUNT_TYPE,
                        ContactsContract.Groups.DELETED,
                        ContactsContract.Groups.GROUP_VISIBLE,
                        ContactsContract.Groups.SYSTEM_ID,
                        ContactsContract.Groups.AUTO_ADD,
                        ContactsContract.Groups.FAVORITES
                };

        String selection =
                ContactsContract.Groups.DELETED
                        + "=0";

        try (
                Cursor cursor =
                        context.getContentResolver()
                                .query(
                                        ContactsContract.Groups
                                                .CONTENT_URI,
                                        projection,
                                        selection,
                                        null,
                                        ContactsContract.Groups.TITLE
                                                + " COLLATE NOCASE ASC"
                                )
        ) {
            if (cursor == null) {
                return groups;
            }

            int idIndex =
                    cursor.getColumnIndex(
                            ContactsContract.Groups._ID
                    );

            int titleIndex =
                    cursor.getColumnIndex(
                            ContactsContract.Groups.TITLE
                    );

            int accountNameIndex =
                    cursor.getColumnIndex(
                            ContactsContract.Groups
                                    .ACCOUNT_NAME
                    );

            int accountTypeIndex =
                    cursor.getColumnIndex(
                            ContactsContract.Groups
                                    .ACCOUNT_TYPE
                    );

            int systemIdIndex =
                    cursor.getColumnIndex(
                            ContactsContract.Groups
                                    .SYSTEM_ID
                    );

            int autoAddIndex =
                    cursor.getColumnIndex(
                            ContactsContract.Groups
                                    .AUTO_ADD
                    );

            int favoritesIndex =
                    cursor.getColumnIndex(
                            ContactsContract.Groups
                                    .FAVORITES
                    );

            while (cursor.moveToNext()) {
                long id =
                        idIndex < 0
                                ? -1L
                                : cursor.getLong(
                                        idIndex
                                );

                String title =
                        titleIndex < 0
                                ? ""
                                : safe(
                                        cursor.getString(
                                                titleIndex
                                        )
                                );

                String systemId =
                        systemIdIndex < 0
                                ? ""
                                : safe(
                                        cursor.getString(
                                                systemIdIndex
                                        )
                                );

                boolean autoAdd =
                        autoAddIndex >= 0
                                && cursor.getInt(
                                        autoAddIndex
                                ) != 0;

                boolean favorites =
                        favoritesIndex >= 0
                                && cursor.getInt(
                                        favoritesIndex
                                ) != 0;

                int memberCount =
                        memberCounts.containsKey(id)
                                ? memberCounts.get(id)
                                : 0;

                if (id <= 0L
                        || title.isEmpty()) {
                    continue;
                }

                if (isHiddenGroupTitle(title)) {
                    continue;
                }

                /*
                 * JARVIS exposes Favorites separately, so Android's
                 * built-in starred/favorites group must not appear as
                 * a second category. Auto-add/system-owned groups are
                 * also implementation details rather than user
                 * categories.
                 */
                if (favorites
                        || autoAdd
                        || !systemId.isEmpty()) {
                    continue;
                }

                /*
                 * Old phones/accounts can leave behind empty legacy
                 * groups such as restored-device or unused class
                 * groups. Do not clutter the JARVIS category bar with
                 * empty groups. Nothing is deleted from Android.
                 */
                if (memberCount <= 0) {
                    continue;
                }

                groups.add(
                        new GroupInfo(
                                id,
                                title,
                                accountNameIndex < 0
                                        ? ""
                                        : cursor.getString(
                                        accountNameIndex
                                ),
                                accountTypeIndex < 0
                                        ? ""
                                        : cursor.getString(
                                        accountTypeIndex
                                )
                        )
                );
            }

        } catch (Exception ignored) {
        }

        return groups;
    }

    public static Map<Long, Set<Long>>
    loadMemberships(
            Context context
    ) {
        Map<Long, Set<Long>> out =
                new LinkedHashMap<>();

        if (context == null) {
            return out;
        }

        String[] projection =
                new String[]{
                        ContactsContract.Data.CONTACT_ID,
                        ContactsContract.CommonDataKinds
                                .GroupMembership.GROUP_ROW_ID
                };

        String selection =
                ContactsContract.Data.MIMETYPE
                        + "=?";

        String[] args =
                new String[]{
                        ContactsContract.CommonDataKinds
                                .GroupMembership
                                .CONTENT_ITEM_TYPE
                };

        try (
                Cursor cursor =
                        context.getContentResolver()
                                .query(
                                        ContactsContract.Data
                                                .CONTENT_URI,
                                        projection,
                                        selection,
                                        args,
                                        null
                                )
        ) {
            if (cursor == null) {
                return out;
            }

            int contactIndex =
                    cursor.getColumnIndex(
                            ContactsContract.Data.CONTACT_ID
                    );

            int groupIndex =
                    cursor.getColumnIndex(
                            ContactsContract.CommonDataKinds
                                    .GroupMembership
                                    .GROUP_ROW_ID
                    );

            while (cursor.moveToNext()) {
                long contactId =
                        contactIndex < 0
                                ? -1L
                                : cursor.getLong(
                                        contactIndex
                                );

                long groupId =
                        groupIndex < 0
                                ? -1L
                                : cursor.getLong(
                                        groupIndex
                                );

                if (contactId <= 0L
                        || groupId <= 0L) {
                    continue;
                }

                Set<Long> groups =
                        out.get(contactId);

                if (groups == null) {
                    groups =
                            new LinkedHashSet<>();

                    out.put(
                            contactId,
                            groups
                    );
                }

                groups.add(groupId);
            }

        } catch (Exception ignored) {
        }

        return out;
    }

    public static List<AccountInfo>
    loadWritableAccountCandidates(
            Context context
    ) {
        LinkedHashMap<String, AccountInfo> preferred =
                new LinkedHashMap<>();

        if (context == null) {
            return new ArrayList<>();
        }

        String[] projection =
                new String[]{
                        ContactsContract.RawContacts
                                .ACCOUNT_NAME,
                        ContactsContract.RawContacts
                                .ACCOUNT_TYPE,
                        ContactsContract.RawContacts
                                .DELETED
                };

        String selection =
                ContactsContract.RawContacts.DELETED
                        + "=0";

        try (
                Cursor cursor =
                        context.getContentResolver()
                                .query(
                                        ContactsContract.RawContacts
                                                .CONTENT_URI,
                                        projection,
                                        selection,
                                        null,
                                        null
                                )
        ) {
            if (cursor != null) {
                int nameIndex =
                        cursor.getColumnIndex(
                                ContactsContract.RawContacts
                                        .ACCOUNT_NAME
                        );

                int typeIndex =
                        cursor.getColumnIndex(
                                ContactsContract.RawContacts
                                        .ACCOUNT_TYPE
                        );

                while (cursor.moveToNext()) {
                    String name =
                            nameIndex < 0
                                    ? ""
                                    : safe(
                                            cursor.getString(
                                                    nameIndex
                                            )
                                    );

                    String type =
                            typeIndex < 0
                                    ? ""
                                    : safe(
                                            cursor.getString(
                                                    typeIndex
                                            )
                                    );

                    if (!isUserFacingWritableAccount(
                            name,
                            type
                    )) {
                        continue;
                    }

                    AccountInfo candidate =
                            new AccountInfo(
                                    normalizeAccountName(
                                            name,
                                            type
                                    ),
                                    type
                            );

                    String displayKey =
                            candidate.label()
                                    .toLowerCase();

                    AccountInfo existing =
                            preferred.get(displayKey);

                    if (existing == null
                            || accountPriority(
                            candidate.type
                    ) > accountPriority(
                            existing.type
                    )) {
                        preferred.put(
                                displayKey,
                                candidate
                        );
                    }
                }
            }

        } catch (Exception ignored) {
        }

        boolean hasDevice = false;

        for (AccountInfo account
                : preferred.values()) {
            String lower =
                    account.type.toLowerCase();

            if (account.type.isEmpty()
                    || "vnd.sec.contact.phone".equals(
                    lower
            )) {
                hasDevice = true;
                break;
            }
        }

        if (!hasDevice) {
            preferred.put(
                    "phone (device)",
                    new AccountInfo(
                            "",
                            ""
                    )
            );
        }

        return new ArrayList<>(
                preferred.values()
        );
    }

    private static boolean isUserFacingWritableAccount(
            String name,
            String type
    ) {
        String lowerName =
                safe(name)
                        .toLowerCase();

        String lowerType =
                safe(type)
                        .toLowerCase();

        if (lowerType.isEmpty()
                || "vnd.sec.contact.phone".equals(
                lowerType
        )) {
            return true;
        }

        if ("com.google".equals(
                lowerType
        )) {
            return true;
        }

        if (lowerType.contains("samsung")
                && !lowerType.contains("meet")
                && !lowerType.contains("calendar")) {
            return true;
        }

        /*
         * These are sync-adapter / app-owned account rows, not useful
         * destinations in a human-facing JARVIS contact editor.
         */
        if (lowerName.contains(
                "primary.sync.account.name"
        )
                || lowerName.contains(
                "sync.account.name"
        )
                || lowerType.contains("meet")
                || lowerType.contains("duo")
                || lowerType.contains("whatsapp")
                || lowerType.contains("telegram")
                || lowerType.contains("signal")
                || lowerType.contains("skype")
                || lowerType.contains("viber")) {
            return false;
        }

        /*
         * Keep normal email-backed accounts available while hiding
         * opaque technical providers with no human-facing identity.
         */
        return lowerName.contains("@");
    }

    private static String normalizeAccountName(
            String name,
            String type
    ) {
        String lowerType =
                safe(type)
                        .toLowerCase();

        if ("vnd.sec.contact.phone".equals(
                lowerType
        )) {
            return "";
        }

        return safe(name);
    }

    private static int accountPriority(
            String type
    ) {
        String lower =
                safe(type)
                        .toLowerCase();

        if ("com.google".equals(lower)) {
            return 30;
        }

        if (lower.contains("samsung")) {
            return 20;
        }

        if (lower.isEmpty()
                || "vnd.sec.contact.phone".equals(
                lower
        )) {
            return 10;
        }

        return 1;
    }

    public static ContactData loadContact(
            Context context,
            long contactId
    ) {
        if (context == null
                || contactId <= 0L) {
            return null;
        }

        String name = "";
        boolean starred = false;
        String photoUri = "";
        String lookupKey = "";

        Uri contactUri =
                Uri.withAppendedPath(
                        ContactsContract.Contacts
                                .CONTENT_URI,
                        Long.toString(contactId)
                );

        String[] contactProjection =
                new String[]{
                        ContactsContract.Contacts._ID,
                        ContactsContract.Contacts
                                .DISPLAY_NAME_PRIMARY,
                        ContactsContract.Contacts.STARRED,
                        ContactsContract.Contacts
                                .PHOTO_URI,
                        ContactsContract.Contacts
                                .LOOKUP_KEY
                };

        try (
                Cursor cursor =
                        context.getContentResolver()
                                .query(
                                        contactUri,
                                        contactProjection,
                                        null,
                                        null,
                                        null
                                )
        ) {
            if (cursor == null
                    || !cursor.moveToFirst()) {
                return null;
            }

            name =
                    column(
                            cursor,
                            ContactsContract.Contacts
                                    .DISPLAY_NAME_PRIMARY
                    );

            starred =
                    intColumn(
                            cursor,
                            ContactsContract.Contacts
                                    .STARRED
                    ) != 0;

            photoUri =
                    column(
                            cursor,
                            ContactsContract.Contacts
                                    .PHOTO_URI
                    );

            lookupKey =
                    column(
                            cursor,
                            ContactsContract.Contacts
                                    .LOOKUP_KEY
                    );

        } catch (Exception ignored) {
            return null;
        }

        long primaryRawId = -1L;
        AccountInfo account =
                new AccountInfo("", "");

        String[] rawProjection =
                new String[]{
                        ContactsContract.RawContacts._ID,
                        ContactsContract.RawContacts
                                .ACCOUNT_NAME,
                        ContactsContract.RawContacts
                                .ACCOUNT_TYPE
                };

        String rawSelection =
                ContactsContract.RawContacts
                        .CONTACT_ID
                        + "=? AND "
                        + ContactsContract.RawContacts
                        .DELETED
                        + "=0";

        String[] rawArgs =
                new String[]{
                        Long.toString(contactId)
                };

        try (
                Cursor cursor =
                        context.getContentResolver()
                                .query(
                                        ContactsContract.RawContacts
                                                .CONTENT_URI,
                                        rawProjection,
                                        rawSelection,
                                        rawArgs,
                                        ContactsContract.RawContacts
                                                ._ID
                                                + " ASC"
                                )
        ) {
            if (cursor != null) {
                while (cursor.moveToNext()) {
                    long rawId =
                            longColumn(
                                    cursor,
                                    ContactsContract.RawContacts
                                            ._ID,
                                    -1L
                            );

                    String accountName =
                            column(
                                    cursor,
                                    ContactsContract.RawContacts
                                            .ACCOUNT_NAME
                            );

                    String accountType =
                            column(
                                    cursor,
                                    ContactsContract.RawContacts
                                            .ACCOUNT_TYPE
                            );

                    if (primaryRawId <= 0L
                            && !looksReadOnlyAccount(
                            accountType
                    )) {
                        primaryRawId = rawId;
                        account =
                                new AccountInfo(
                                        accountName,
                                        accountType
                                );
                    }

                    if (primaryRawId <= 0L) {
                        primaryRawId = rawId;
                        account =
                                new AccountInfo(
                                        accountName,
                                        accountType
                                );
                    }
                }
            }

        } catch (Exception ignored) {
        }

        List<PhoneData> phones =
                new ArrayList<>();

        String[] phoneProjection =
                new String[]{
                        ContactsContract.CommonDataKinds
                                .Phone._ID,
                        ContactsContract.CommonDataKinds
                                .Phone.RAW_CONTACT_ID,
                        ContactsContract.CommonDataKinds
                                .Phone.NUMBER,
                        ContactsContract.CommonDataKinds
                                .Phone.TYPE,
                        ContactsContract.CommonDataKinds
                                .Phone.LABEL
                };

        String phoneSelection =
                ContactsContract.CommonDataKinds.Phone
                        .CONTACT_ID
                        + "=?";

        try (
                Cursor cursor =
                        context.getContentResolver()
                                .query(
                                        ContactsContract
                                                .CommonDataKinds
                                                .Phone.CONTENT_URI,
                                        phoneProjection,
                                        phoneSelection,
                                        rawArgs,
                                        null
                                )
        ) {
            if (cursor != null) {
                while (cursor.moveToNext()) {
                    phones.add(
                            new PhoneData(
                                    longColumn(
                                            cursor,
                                            ContactsContract
                                                    .CommonDataKinds
                                                    .Phone._ID,
                                            -1L
                                    ),
                                    longColumn(
                                            cursor,
                                            ContactsContract
                                                    .CommonDataKinds
                                                    .Phone
                                                    .RAW_CONTACT_ID,
                                            -1L
                                    ),
                                    column(
                                            cursor,
                                            ContactsContract
                                                    .CommonDataKinds
                                                    .Phone.NUMBER
                                    ),
                                    intColumn(
                                            cursor,
                                            ContactsContract
                                                    .CommonDataKinds
                                                    .Phone.TYPE
                                    ),
                                    column(
                                            cursor,
                                            ContactsContract
                                                    .CommonDataKinds
                                                    .Phone.LABEL
                                    )
                            )
                    );
                }
            }

        } catch (Exception ignored) {
        }

        Set<Long> groupIds =
                new LinkedHashSet<>();

        String groupSelection =
                ContactsContract.Data.CONTACT_ID
                        + "=? AND "
                        + ContactsContract.Data.MIMETYPE
                        + "=?";

        String[] groupArgs =
                new String[]{
                        Long.toString(contactId),
                        ContactsContract.CommonDataKinds
                                .GroupMembership
                                .CONTENT_ITEM_TYPE
                };

        String[] groupProjection =
                new String[]{
                        ContactsContract.CommonDataKinds
                                .GroupMembership.GROUP_ROW_ID
                };

        try (
                Cursor cursor =
                        context.getContentResolver()
                                .query(
                                        ContactsContract.Data
                                                .CONTENT_URI,
                                        groupProjection,
                                        groupSelection,
                                        groupArgs,
                                        null
                                )
        ) {
            if (cursor != null) {
                int groupIndex =
                        cursor.getColumnIndex(
                                ContactsContract
                                        .CommonDataKinds
                                        .GroupMembership
                                        .GROUP_ROW_ID
                        );

                while (cursor.moveToNext()) {
                    long groupId =
                            groupIndex < 0
                                    ? -1L
                                    : cursor.getLong(
                                            groupIndex
                                    );

                    if (groupId > 0L) {
                        groupIds.add(groupId);
                    }
                }
            }

        } catch (Exception ignored) {
        }

        return new ContactData(
                contactId,
                name,
                starred,
                photoUri,
                lookupKey,
                primaryRawId,
                account,
                phones,
                groupIds
        );
    }

    public static SaveResult createContact(
            Context context,
            String name,
            List<PhoneEdit> phones,
            boolean starred,
            AccountInfo account,
            Set<Long> groupIds,
            byte[] photoBytes
    ) {
        if (!canWrite(context)) {
            return SaveResult.fail(
                    "Contacts write permission is required."
            );
        }

        String cleanName =
                safe(name);

        if (cleanName.isEmpty()) {
            return SaveResult.fail(
                    "Name is required."
            );
        }

        ArrayList<ContentProviderOperation> ops =
                new ArrayList<>();

        ContentProviderOperation.Builder raw =
                ContentProviderOperation
                        .newInsert(
                                ContactsContract.RawContacts
                                        .CONTENT_URI
                        )
                        .withValue(
                                ContactsContract.RawContacts
                                        .ACCOUNT_NAME,
                                emptyToNull(
                                        account == null
                                                ? ""
                                                : account.name
                                )
                        )
                        .withValue(
                                ContactsContract.RawContacts
                                        .ACCOUNT_TYPE,
                                emptyToNull(
                                        account == null
                                                ? ""
                                                : account.type
                                )
                        )
                        .withValue(
                                ContactsContract.RawContacts
                                        .STARRED,
                                starred ? 1 : 0
                        );

        ops.add(raw.build());

        ops.add(
                ContentProviderOperation
                        .newInsert(
                                ContactsContract.Data
                                        .CONTENT_URI
                        )
                        .withValueBackReference(
                                ContactsContract.Data
                                        .RAW_CONTACT_ID,
                                0
                        )
                        .withValue(
                                ContactsContract.Data
                                        .MIMETYPE,
                                ContactsContract
                                        .CommonDataKinds
                                        .StructuredName
                                        .CONTENT_ITEM_TYPE
                        )
                        .withValue(
                                ContactsContract
                                        .CommonDataKinds
                                        .StructuredName
                                        .DISPLAY_NAME,
                                cleanName
                        )
                        .build()
        );

        for (PhoneEdit phone : phones) {
            String number =
                    safe(phone.number);

            if (number.isEmpty()) {
                continue;
            }

            ops.add(
                    ContentProviderOperation
                            .newInsert(
                                    ContactsContract.Data
                                            .CONTENT_URI
                            )
                            .withValueBackReference(
                                    ContactsContract.Data
                                            .RAW_CONTACT_ID,
                                    0
                            )
                            .withValue(
                                    ContactsContract.Data
                                            .MIMETYPE,
                                    ContactsContract
                                            .CommonDataKinds
                                            .Phone
                                            .CONTENT_ITEM_TYPE
                            )
                            .withValue(
                                    ContactsContract
                                            .CommonDataKinds
                                            .Phone.NUMBER,
                                    number
                            )
                            .withValue(
                                    ContactsContract
                                            .CommonDataKinds
                                            .Phone.TYPE,
                                    phone.type
                            )
                            .withValue(
                                    ContactsContract
                                            .CommonDataKinds
                                            .Phone.LABEL,
                                    emptyToNull(
                                            phone.customLabel
                                    )
                            )
                            .build()
            );
        }

        if (groupIds != null) {
            for (Long groupId : groupIds) {
                if (groupId == null
                        || groupId <= 0L) {
                    continue;
                }

                ops.add(
                        ContentProviderOperation
                                .newInsert(
                                        ContactsContract.Data
                                                .CONTENT_URI
                                )
                                .withValueBackReference(
                                        ContactsContract.Data
                                                .RAW_CONTACT_ID,
                                        0
                                )
                                .withValue(
                                        ContactsContract.Data
                                                .MIMETYPE,
                                        ContactsContract
                                                .CommonDataKinds
                                                .GroupMembership
                                                .CONTENT_ITEM_TYPE
                                )
                                .withValue(
                                        ContactsContract
                                                .CommonDataKinds
                                                .GroupMembership
                                                .GROUP_ROW_ID,
                                        groupId
                                )
                                .build()
                );
            }
        }

        if (photoBytes != null
                && photoBytes.length > 0) {
            ops.add(
                    ContentProviderOperation
                            .newInsert(
                                    ContactsContract.Data
                                            .CONTENT_URI
                            )
                            .withValueBackReference(
                                    ContactsContract.Data
                                            .RAW_CONTACT_ID,
                                    0
                            )
                            .withValue(
                                    ContactsContract.Data
                                            .MIMETYPE,
                                    ContactsContract
                                            .CommonDataKinds
                                            .Photo.CONTENT_ITEM_TYPE
                            )
                            .withValue(
                                    ContactsContract
                                            .CommonDataKinds
                                            .Photo.PHOTO,
                                    photoBytes
                            )
                            .withValue(
                                    ContactsContract.Data
                                            .IS_SUPER_PRIMARY,
                                    1
                            )
                            .build()
            );
        }

        try {
            context.getContentResolver()
                    .applyBatch(
                            ContactsContract.AUTHORITY,
                            ops
                    );

            long createdId =
                    findNewestContactIdByName(
                            context,
                            cleanName
                    );

            return SaveResult.ok(createdId);

        } catch (
                RemoteException
                        | OperationApplicationException
                        | SecurityException ex
        ) {
            return SaveResult.fail(
                    ex.getMessage() == null
                            ? "Unable to create contact."
                            : ex.getMessage()
            );
        }
    }

    public static SaveResult updateContact(
            Context context,
            ContactData original,
            String name,
            List<PhoneEdit> phones,
            boolean starred,
            Set<Long> selectedGroupIds,
            byte[] photoBytes,
            boolean removePhoto
    ) {
        if (!canWrite(context)) {
            return SaveResult.fail(
                    "Contacts write permission is required."
            );
        }

        if (original == null
                || original.contactId <= 0L
                || original.primaryRawContactId <= 0L) {
            return SaveResult.fail(
                    "Contact cannot be edited."
            );
        }

        String cleanName =
                safe(name);

        if (cleanName.isEmpty()) {
            return SaveResult.fail(
                    "Name is required."
            );
        }

        ContentResolver resolver =
                context.getContentResolver();

        updateStarred(
                resolver,
                original.contactId,
                starred
        );

        saveName(
                resolver,
                original.primaryRawContactId,
                cleanName
        );

        savePhones(
                resolver,
                original.primaryRawContactId,
                phones
        );

        saveGroups(
                resolver,
                original,
                selectedGroupIds
        );

        if (removePhoto) {
            removePhoto(
                    resolver,
                    original.contactId
            );
        } else if (photoBytes != null
                && photoBytes.length > 0) {
            savePhoto(
                    resolver,
                    original.primaryRawContactId,
                    original.contactId,
                    photoBytes
            );
        }

        return SaveResult.ok(
                original.contactId
        );
    }

    public static GroupInfo createGroup(
            Context context,
            String title,
            AccountInfo account
    ) {
        if (!canWrite(context)) {
            return null;
        }

        String cleanTitle =
                safe(title);

        if (cleanTitle.isEmpty()) {
            return null;
        }

        ContentValues values =
                new ContentValues();

        values.put(
                ContactsContract.Groups.TITLE,
                cleanTitle
        );

        values.put(
                ContactsContract.Groups.GROUP_VISIBLE,
                1
        );

        if (account != null) {
            if (!account.name.isEmpty()) {
                values.put(
                        ContactsContract.Groups.ACCOUNT_NAME,
                        account.name
                );
            }

            if (!account.type.isEmpty()) {
                values.put(
                        ContactsContract.Groups.ACCOUNT_TYPE,
                        account.type
                );
            }
        }

        try {
            Uri created =
                    context.getContentResolver()
                            .insert(
                                    ContactsContract.Groups.CONTENT_URI,
                                    values
                            );

            if (created == null) {
                return null;
            }

            long id =
                    Long.parseLong(
                            created.getLastPathSegment()
                    );

            return new GroupInfo(
                    id,
                    cleanTitle,
                    account == null
                            ? ""
                            : account.name,
                    account == null
                            ? ""
                            : account.type
            );

        } catch (Exception ignored) {
            return null;
        }
    }

    public static boolean deleteGroup(
            Context context,
            long groupId
    ) {
        if (!canWrite(context)
                || groupId <= 0L) {
            return false;
        }

        try {
            Uri groupUri =
                    Uri.withAppendedPath(
                            ContactsContract.Groups
                                    .CONTENT_URI,
                            Long.toString(groupId)
                    );

            int rows =
                    context.getContentResolver()
                            .delete(
                                    groupUri,
                                    null,
                                    null
                            );

            return rows > 0;

        } catch (Exception ignored) {
            return false;
        }
    }

    public static boolean deleteContact(
            Context context,
            long contactId
    ) {
        if (!canWrite(context)
                || contactId <= 0L) {
            return false;
        }

        try {
            int rows =
                    context.getContentResolver()
                            .delete(
                                    ContactsContract.RawContacts
                                            .CONTENT_URI,
                                    ContactsContract.RawContacts
                                            .CONTACT_ID
                                            + "=?",
                                    new String[]{
                                            Long.toString(
                                                    contactId
                                            )
                                    }
                            );

            return rows > 0;

        } catch (Exception ignored) {
            return false;
        }
    }

    private static void updateStarred(
            ContentResolver resolver,
            long contactId,
            boolean starred
    ) {
        ContentValues values =
                new ContentValues();

        values.put(
                ContactsContract.RawContacts
                        .STARRED,
                starred ? 1 : 0
        );

        resolver.update(
                ContactsContract.RawContacts
                        .CONTENT_URI,
                values,
                ContactsContract.RawContacts
                        .CONTACT_ID
                        + "=?",
                new String[]{
                        Long.toString(contactId)
                }
        );
    }

    private static void saveName(
            ContentResolver resolver,
            long rawContactId,
            String name
    ) {
        String selection =
                ContactsContract.Data.RAW_CONTACT_ID
                        + "=? AND "
                        + ContactsContract.Data.MIMETYPE
                        + "=?";

        String[] args =
                new String[]{
                        Long.toString(rawContactId),
                        ContactsContract.CommonDataKinds
                                .StructuredName
                                .CONTENT_ITEM_TYPE
                };

        ContentValues values =
                new ContentValues();

        values.put(
                ContactsContract.CommonDataKinds
                        .StructuredName.DISPLAY_NAME,
                name
        );

        int rows =
                resolver.update(
                        ContactsContract.Data
                                .CONTENT_URI,
                        values,
                        selection,
                        args
                );

        if (rows == 0) {
            values.put(
                    ContactsContract.Data
                            .RAW_CONTACT_ID,
                    rawContactId
            );

            values.put(
                    ContactsContract.Data.MIMETYPE,
                    ContactsContract.CommonDataKinds
                            .StructuredName
                            .CONTENT_ITEM_TYPE
            );

            resolver.insert(
                    ContactsContract.Data
                            .CONTENT_URI,
                    values
            );
        }
    }

    private static void savePhones(
            ContentResolver resolver,
            long primaryRawContactId,
            List<PhoneEdit> phones
    ) {
        for (PhoneEdit phone : phones) {
            String number =
                    safe(phone.number);

            if (phone.dataId > 0L) {
                Uri uri =
                        Uri.withAppendedPath(
                                ContactsContract.Data
                                        .CONTENT_URI,
                                Long.toString(
                                        phone.dataId
                                )
                        );

                if (number.isEmpty()) {
                    resolver.delete(
                            uri,
                            null,
                            null
                    );
                    continue;
                }

                ContentValues values =
                        new ContentValues();

                values.put(
                        ContactsContract.CommonDataKinds
                                .Phone.NUMBER,
                        number
                );

                values.put(
                        ContactsContract.CommonDataKinds
                                .Phone.TYPE,
                        phone.type
                );

                values.put(
                        ContactsContract.CommonDataKinds
                                .Phone.LABEL,
                        emptyToNull(
                                phone.customLabel
                        )
                );

                resolver.update(
                        uri,
                        values,
                        null,
                        null
                );

            } else if (!number.isEmpty()) {

                ContentValues values =
                        new ContentValues();

                values.put(
                        ContactsContract.Data
                                .RAW_CONTACT_ID,
                        primaryRawContactId
                );

                values.put(
                        ContactsContract.Data
                                .MIMETYPE,
                        ContactsContract.CommonDataKinds
                                .Phone.CONTENT_ITEM_TYPE
                );

                values.put(
                        ContactsContract.CommonDataKinds
                                .Phone.NUMBER,
                        number
                );

                values.put(
                        ContactsContract.CommonDataKinds
                                .Phone.TYPE,
                        phone.type
                );

                values.put(
                        ContactsContract.CommonDataKinds
                                .Phone.LABEL,
                        emptyToNull(
                                phone.customLabel
                        )
                );

                resolver.insert(
                        ContactsContract.Data
                                .CONTENT_URI,
                        values
                );
            }
        }
    }

    private static void saveGroups(
            ContentResolver resolver,
            ContactData original,
            Set<Long> selectedGroupIds
    ) {
        Set<Long> selected =
                selectedGroupIds == null
                        ? new LinkedHashSet<>()
                        : selectedGroupIds;

        Set<Long> existing =
                original.groupIds == null
                        ? new LinkedHashSet<>()
                        : original.groupIds;

        for (Long groupId : existing) {
            if (groupId == null
                    || groupId <= 0L
                    || selected.contains(
                    groupId
            )) {
                continue;
            }

            resolver.delete(
                    ContactsContract.Data
                            .CONTENT_URI,
                    ContactsContract.Data.CONTACT_ID
                            + "=? AND "
                            + ContactsContract.Data.MIMETYPE
                            + "=? AND "
                            + ContactsContract.CommonDataKinds
                            .GroupMembership.GROUP_ROW_ID
                            + "=?",
                    new String[]{
                            Long.toString(
                                    original.contactId
                            ),
                            ContactsContract.CommonDataKinds
                                    .GroupMembership
                                    .CONTENT_ITEM_TYPE,
                            Long.toString(groupId)
                    }
            );
        }

        for (Long groupId : selected) {
            if (groupId == null
                    || groupId <= 0L
                    || existing.contains(
                    groupId
            )) {
                continue;
            }

            ContentValues values =
                    new ContentValues();

            values.put(
                    ContactsContract.Data
                            .RAW_CONTACT_ID,
                    original.primaryRawContactId
            );

            values.put(
                    ContactsContract.Data.MIMETYPE,
                    ContactsContract.CommonDataKinds
                            .GroupMembership
                            .CONTENT_ITEM_TYPE
            );

            values.put(
                    ContactsContract.CommonDataKinds
                            .GroupMembership
                            .GROUP_ROW_ID,
                    groupId
            );

            resolver.insert(
                    ContactsContract.Data
                            .CONTENT_URI,
                    values
            );
        }
    }

    private static void savePhoto(
            ContentResolver resolver,
            long rawContactId,
            long contactId,
            byte[] photoBytes
    ) {
        removePhoto(
                resolver,
                contactId
        );

        ContentValues values =
                new ContentValues();

        values.put(
                ContactsContract.Data
                        .RAW_CONTACT_ID,
                rawContactId
        );

        values.put(
                ContactsContract.Data.MIMETYPE,
                ContactsContract.CommonDataKinds
                        .Photo.CONTENT_ITEM_TYPE
        );

        values.put(
                ContactsContract.CommonDataKinds
                        .Photo.PHOTO,
                photoBytes
        );

        values.put(
                ContactsContract.Data
                        .IS_SUPER_PRIMARY,
                1
        );

        resolver.insert(
                ContactsContract.Data
                        .CONTENT_URI,
                values
        );
    }

    private static void removePhoto(
            ContentResolver resolver,
            long contactId
    ) {
        resolver.delete(
                ContactsContract.Data.CONTENT_URI,
                ContactsContract.Data.CONTACT_ID
                        + "=? AND "
                        + ContactsContract.Data.MIMETYPE
                        + "=?",
                new String[]{
                        Long.toString(contactId),
                        ContactsContract.CommonDataKinds
                                .Photo.CONTENT_ITEM_TYPE
                }
        );
    }

    private static long findNewestContactIdByName(
            Context context,
            String name
    ) {
        Uri uri =
                Uri.withAppendedPath(
                        ContactsContract.Contacts
                                .CONTENT_FILTER_URI,
                        Uri.encode(name)
                );

        String[] projection =
                new String[]{
                        ContactsContract.Contacts._ID,
                        ContactsContract.Contacts
                                .DISPLAY_NAME_PRIMARY
                };

        try (
                Cursor cursor =
                        context.getContentResolver()
                                .query(
                                        uri,
                                        projection,
                                        null,
                                        null,
                                        ContactsContract.Contacts
                                                ._ID
                                                + " DESC"
                                )
        ) {
            if (cursor != null
                    && cursor.moveToFirst()) {
                return longColumn(
                        cursor,
                        ContactsContract.Contacts._ID,
                        -1L
                );
            }

        } catch (Exception ignored) {
        }

        return -1L;
    }

    private static boolean isHiddenGroupTitle(
            String title
    ) {
        String lower =
                safe(title)
                        .toLowerCase();

        if (lower.isEmpty()) {
            return true;
        }

        if ("ice".equals(lower)
                || lower.contains(
                "in case of emergency"
        )
                || "my contacts".equals(lower)
                || "starred in android".equals(lower)) {
            return true;
        }

        /*
         * Legacy import groups can survive migrations for years.
         * JARVIS hides them but never deletes them automatically.
         */
        return lower.contains(
                "restored from"
        );
    }

    private static boolean looksReadOnlyAccount(
            String accountType
    ) {
        String type =
                safe(accountType)
                        .toLowerCase();

        return type.contains("whatsapp")
                || type.contains("telegram")
                || type.contains("skype")
                || type.contains("signal")
                || type.contains("viber")
                || type.contains("duo");
    }

    private static String emptyToNull(
            String value
    ) {
        String clean =
                safe(value);

        return clean.isEmpty()
                ? null
                : clean;
    }

    private static String column(
            Cursor cursor,
            String name
    ) {
        int index =
                cursor.getColumnIndex(name);

        if (index < 0) {
            return "";
        }

        return safe(
                cursor.getString(index)
        );
    }

    private static int intColumn(
            Cursor cursor,
            String name
    ) {
        int index =
                cursor.getColumnIndex(name);

        return index < 0
                ? 0
                : cursor.getInt(index);
    }

    private static long longColumn(
            Cursor cursor,
            String name,
            long fallback
    ) {
        int index =
                cursor.getColumnIndex(name);

        return index < 0
                ? fallback
                : cursor.getLong(index);
    }

    private static String safe(
            String value
    ) {
        return value == null
                ? ""
                : value.trim();
    }
}
