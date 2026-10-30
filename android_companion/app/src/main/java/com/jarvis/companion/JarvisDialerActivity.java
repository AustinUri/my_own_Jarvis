package com.jarvis.companion;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.CallLog;
import android.provider.ContactsContract;
import android.telephony.PhoneNumberUtils;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.GridLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Space;
import android.widget.TextView;
import android.widget.Toast;

import java.text.DateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public final class JarvisDialerActivity extends Activity {

    public static final String EXTRA_ADD_CALL_MODE =
            "jarvis_add_call_mode";

    private static final int REQUEST_CALL_PHONE = 2302;
    private static final int REQUEST_CONTACTS = 2304;
    private static final int REQUEST_CALL_LOG = 2305;

    private static final int BG = Color.rgb(4, 9, 16);
    private static final int CARD = Color.rgb(15, 23, 34);
    private static final int CARD_2 = Color.rgb(23, 34, 48);
    private static final int TEXT = Color.rgb(248, 250, 252);
    private static final int MUTED = Color.rgb(148, 163, 184);
    private static final int ORANGE = Color.rgb(255, 153, 61);
    private static final int GREEN = Color.rgb(43, 190, 102);

    private LinearLayout content;
    private LinearLayout nav;
    private TextView tabRecents;
    private TextView tabContacts;
    private TextView tabKeypad;
    private String pendingNumber = "";
    private boolean addCallMode = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        addCallMode =
                getIntent() != null
                        && getIntent().getBooleanExtra(
                                EXTRA_ADD_CALL_MODE,
                                false
                        );

        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);

        View root = buildShell();
        setContentView(root);
        applySystemInsets(root);

        String incoming = numberFromIntent();

        if (!incoming.isEmpty()) {
            showKeypad(incoming);
        } else {
            showRecents();
        }
    }

    private View buildShell() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);

        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.VERTICAL);
        top.setPadding(dp(22), dp(22), dp(22), dp(10));

        TextView brand = new TextView(this);
        brand.setText("J A R V I S");
        brand.setTextColor(ORANGE);
        brand.setTextSize(12f);
        brand.setTypeface(Typeface.DEFAULT_BOLD);
        brand.setLetterSpacing(0.14f);

        TextView title = new TextView(this);
        title.setText("Phone");
        title.setTextColor(TEXT);
        title.setTextSize(31f);
        title.setTypeface(Typeface.DEFAULT_BOLD);

        top.addView(brand);
        top.addView(title);
        root.addView(top);

        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(16), dp(5), dp(16), dp(10));

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.addView(
                content,
                new ScrollView.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                )
        );

        root.addView(
                scroll,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        0,
                        1f
                )
        );

        nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setBackgroundColor(Color.rgb(9, 16, 27));

        tabRecents =
                navItem(
                        "Recents",
                        v -> showRecents()
                );

        tabContacts =
                navItem(
                        "Contacts",
                        v -> showContacts()
                );

        tabKeypad =
                navItem(
                        "Keypad",
                        v -> showKeypad("")
                );

        nav.addView(tabRecents, navWeight());
        nav.addView(tabContacts, navWeight());
        nav.addView(tabKeypad, navWeight());

        root.addView(nav);

        return root;
    }

    private void applySystemInsets(View root) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            root.setOnApplyWindowInsetsListener(
                    (view, insets) -> {
                        android.graphics.Insets bars =
                                insets.getInsets(
                                        WindowInsets.Type.navigationBars()
                                );

                        nav.setPadding(
                                dp(8),
                                dp(7),
                                dp(8),
                                bars.bottom + dp(18)
                        );

                        return insets;
                    }
            );
            root.requestApplyInsets();
        } else {
            nav.setPadding(
                    dp(8),
                    dp(7),
                    dp(8),
                    dp(32)
            );
        }
    }

    private void showRecents() {
        selectTab(tabRecents);
        clearContent();

        header(
                "Recent calls",
                "Tap CALL to call back"
        );

        if (checkSelfPermission(
                Manifest.permission.READ_CALL_LOG
        ) != PackageManager.PERMISSION_GRANTED) {

            permissionCard(
                    "Call history permission",
                    "Allow access to display recent calls.",
                    v -> requestPermissions(
                            new String[]{
                                    Manifest.permission.READ_CALL_LOG
                            },
                            REQUEST_CALL_LOG
                    )
            );
            return;
        }

        List<RecentRow> rows = loadRecents(60);

        if (rows.isEmpty()) {
            emptyCard("No recent calls available");
            return;
        }

        for (RecentRow row : rows) {
            content.addView(
                    recentRow(row),
                    fullWidthWrap(dp(6), dp(6))
            );
        }
    }

    private void showContacts() {
        selectTab(tabContacts);
        clearContent();

        LinearLayout headingRow = new LinearLayout(this);
        headingRow.setOrientation(LinearLayout.HORIZONTAL);
        headingRow.setGravity(Gravity.CENTER_VERTICAL);

        LinearLayout headingBlock = new LinearLayout(this);
        headingBlock.setOrientation(LinearLayout.VERTICAL);
        headingBlock.addView(headingText("Contacts"));
        headingBlock.addView(
                smallText(
                        "One person once — all numbers grouped together"
                )
        );

        TextView add = chip("+ ADD", ORANGE, Color.WHITE);
        add.setOnClickListener(v -> addContact());

        headingRow.addView(
                headingBlock,
                new LinearLayout.LayoutParams(
                        0,
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        1f
                )
        );
        headingRow.addView(add);
        content.addView(headingRow);

        if (checkSelfPermission(
                Manifest.permission.READ_CONTACTS
        ) != PackageManager.PERMISSION_GRANTED) {

            permissionCard(
                    "Contacts permission",
                    "Allow Contacts access for names and photos.",
                    v -> requestPermissions(
                            new String[]{
                                    Manifest.permission.READ_CONTACTS
                            },
                            REQUEST_CONTACTS
                    )
            );
            return;
        }

        EditText search = new EditText(this);
        search.setHint("Search contacts");
        search.setHintTextColor(MUTED);
        search.setTextColor(TEXT);
        search.setTextSize(16f);
        search.setSingleLine(true);
        search.setPadding(
                dp(17),
                dp(13),
                dp(17),
                dp(13)
        );
        search.setBackground(
                rounded(CARD, dp(18))
        );

        content.addView(
                search,
                fullWidthWrap(dp(14), dp(7))
        );

        LinearLayout results = new LinearLayout(this);
        results.setOrientation(LinearLayout.VERTICAL);
        content.addView(results);

        Runnable reload =
                () -> renderContacts(
                        results,
                        search.getText().toString()
                );

        search.addTextChangedListener(
                new android.text.TextWatcher() {

            @Override
            public void beforeTextChanged(
                    CharSequence s,
                    int start,
                    int count,
                    int after
            ) {
            }

            @Override
            public void onTextChanged(
                    CharSequence s,
                    int start,
                    int before,
                    int count
            ) {
                reload.run();
            }

            @Override
            public void afterTextChanged(
                    android.text.Editable s
            ) {
            }
        });

        reload.run();
    }

    private void showKeypad(String initialNumber) {
        selectTab(tabKeypad);
        clearContent();

        header(
                "Keypad",
                "Long-press 0 for +"
        );

        LinearLayout suggestions =
                new LinearLayout(this);
        suggestions.setOrientation(
                LinearLayout.VERTICAL
        );
        content.addView(suggestions);

        LinearLayout numberRow =
                new LinearLayout(this);
        numberRow.setOrientation(
                LinearLayout.HORIZONTAL
        );
        numberRow.setGravity(
                Gravity.CENTER_VERTICAL
        );

        EditText number = new EditText(this);
        number.setText(initialNumber);
        number.setTextColor(TEXT);
        number.setHintTextColor(MUTED);
        number.setTextSize(30f);
        number.setGravity(Gravity.CENTER);
        number.setSingleLine(true);
        number.setInputType(
                android.text.InputType.TYPE_CLASS_PHONE
        );
        number.setShowSoftInputOnFocus(false);
        number.setBackgroundColor(Color.TRANSPARENT);

        TextView backspace =
                chip("\u232b", CARD_2, TEXT);
        backspace.setTextSize(24f);

        backspace.setOnClickListener(
                v -> deleteOne(number)
        );

        backspace.setOnLongClickListener(
                v -> {
                    number.setText("");
                    return true;
                }
        );

        numberRow.addView(
                number,
                new LinearLayout.LayoutParams(
                        0,
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        1f
                )
        );
        numberRow.addView(backspace);

        content.addView(
                numberRow,
                fullWidthWrap(dp(8), dp(8))
        );

        number.addTextChangedListener(
                new android.text.TextWatcher() {

            @Override
            public void beforeTextChanged(
                    CharSequence s,
                    int start,
                    int count,
                    int after
            ) {
            }

            @Override
            public void onTextChanged(
                    CharSequence s,
                    int start,
                    int before,
                    int count
            ) {
                renderDialMatches(
                        suggestions,
                        s == null
                                ? ""
                                : s.toString()
                );
            }

            @Override
            public void afterTextChanged(
                    android.text.Editable s
            ) {
            }
        });

        GridLayout grid = new GridLayout(this);
        grid.setColumnCount(3);
        grid.setAlignmentMode(
                GridLayout.ALIGN_BOUNDS
        );

        String[] keys = new String[]{
                "1", "2", "3",
                "4", "5", "6",
                "7", "8", "9",
                "*", "0", "#"
        };

        for (String key : keys) {
            TextView button = keypadButton(key);

            button.setOnClickListener(
                    v -> number.append(
                            ((TextView) v)
                                    .getTag()
                                    .toString()
                    )
            );

            if ("0".equals(key)) {
                button.setOnLongClickListener(
                        v -> {
                            number.append("+");
                            return true;
                        }
                );
            }

            GridLayout.LayoutParams lp =
                    new GridLayout.LayoutParams();
            lp.width = 0;
            lp.height = dp(82);
            lp.columnSpec =
                    GridLayout.spec(
                            GridLayout.UNDEFINED,
                            1f
                    );
            lp.setMargins(
                    dp(9),
                    dp(8),
                    dp(9),
                    dp(8)
            );

            grid.addView(button, lp);
        }

        content.addView(grid);

        LinearLayout extras =
                new LinearLayout(this);
        extras.setOrientation(
                LinearLayout.HORIZONTAL
        );
        extras.setGravity(Gravity.CENTER);
        extras.setVisibility(View.GONE);

        TextView pause =
                chip("Pause  ,", CARD_2, TEXT);
        pause.setOnClickListener(
                v -> number.append(
                        String.valueOf(
                                PhoneNumberUtils.PAUSE
                        )
                )
        );

        TextView wait =
                chip("Wait  ;", CARD_2, TEXT);
        wait.setOnClickListener(
                v -> number.append(
                        String.valueOf(
                                PhoneNumberUtils.WAIT
                        )
                )
        );

        TextView plus =
                chip("+", CARD_2, TEXT);
        plus.setOnClickListener(
                v -> number.append("+")
        );

        extras.addView(pause);
        extras.addView(space(dp(8)));
        extras.addView(wait);
        extras.addView(space(dp(8)));
        extras.addView(plus);

        TextView more =
                chip(
                        "\u22ef  More",
                        CARD_2,
                        TEXT
                );
        more.setOnClickListener(
                v -> extras.setVisibility(
                        extras.getVisibility()
                                == View.VISIBLE
                                ? View.GONE
                                : View.VISIBLE
                )
        );

        LinearLayout controlRow =
                new LinearLayout(this);
        controlRow.setOrientation(
                LinearLayout.HORIZONTAL
        );
        controlRow.setGravity(Gravity.CENTER);
        controlRow.addView(more);

        content.addView(
                controlRow,
                fullWidthWrap(dp(10), dp(8))
        );
        content.addView(
                extras,
                fullWidthWrap(0, dp(12))
        );

        TextView call =
                chip(
                        "\u260e   CALL",
                        GREEN,
                        Color.WHITE
                );
        call.setTextSize(18f);
        call.setGravity(Gravity.CENTER);
        call.setPadding(
                dp(18),
                dp(17),
                dp(18),
                dp(17)
        );
        call.setOnClickListener(
                v -> placeCall(
                        number.getText().toString()
                )
        );

        content.addView(
                call,
                fullWidthWrap(dp(8), dp(12))
        );

        renderDialMatches(
                suggestions,
                initialNumber
        );
    }

    private void renderDialMatches(
            LinearLayout target,
            String typed
    ) {
        target.removeAllViews();

        String normalized =
                JarvisCallerIdentity.normalize(
                        typed
                );

        if (normalized.length() < 2
                || checkSelfPermission(
                Manifest.permission.READ_CONTACTS
        ) != PackageManager.PERMISSION_GRANTED) {
            return;
        }

        List<ContactRow> matches =
                findNumberMatches(
                        typed,
                        3
                );

        for (ContactRow row : matches) {
            LinearLayout card =
                    contactCard(
                            row,
                            false
                    );

            card.setOnClickListener(
                    v -> chooseNumberAndCall(row)
            );

            target.addView(
                    card,
                    fullWidthWrap(
                            dp(4),
                            dp(4)
                    )
            );
        }
    }

    private List<ContactRow> findNumberMatches(
            String typed,
            int limit
    ) {
        String normalizedTyped =
                JarvisCallerIdentity.normalize(
                        typed
                );

        List<ContactRow> all =
                loadContacts("", 500);

        List<ContactRow> out =
                new ArrayList<>();

        for (ContactRow row : all) {
            for (PhoneEntry phone : row.numbers) {
                if (phone.normalized.contains(
                        normalizedTyped
                )) {
                    out.add(row);
                    break;
                }
            }

            if (out.size() >= limit) {
                break;
            }
        }

        return out;
    }

    private void renderContacts(
            LinearLayout target,
            String filter
    ) {
        target.removeAllViews();

        List<ContactRow> rows =
                loadContacts(
                        filter,
                        150
                );

        if (rows.isEmpty()) {
            target.addView(
                    smallText(
                            "No contacts found"
                    )
            );
            return;
        }

        for (ContactRow row : rows) {
            target.addView(
                    contactCard(
                            row,
                            true
                    ),
                    fullWidthWrap(
                            dp(6),
                            dp(6)
                    )
            );
        }
    }

    private List<ContactRow> loadContacts(
            String filter,
            int limit
    ) {
        String cleanFilter =
                filter == null
                        ? ""
                        : filter.trim();

        Map<Long, ContactRow> contacts =
                loadVisibleContactBases(
                        cleanFilter
                );

        if (contacts.isEmpty()) {
            return new ArrayList<>();
        }

        String[] projection =
                new String[]{
                        ContactsContract.CommonDataKinds.Phone
                                .CONTACT_ID,
                        ContactsContract.CommonDataKinds.Phone
                                .NUMBER,
                        ContactsContract.CommonDataKinds.Phone
                                .TYPE,
                        ContactsContract.CommonDataKinds.Phone
                                .LABEL
                };

        try (
                Cursor cursor =
                        getContentResolver().query(
                                ContactsContract.CommonDataKinds.Phone
                                        .CONTENT_URI,
                                projection,
                                null,
                                null,
                                null
                        )
        ) {
            if (cursor != null) {
                int idIndex =
                        cursor.getColumnIndex(
                                ContactsContract.CommonDataKinds.Phone
                                        .CONTACT_ID
                        );

                int numberIndex =
                        cursor.getColumnIndex(
                                ContactsContract.CommonDataKinds.Phone
                                        .NUMBER
                        );

                int typeIndex =
                        cursor.getColumnIndex(
                                ContactsContract.CommonDataKinds.Phone
                                        .TYPE
                        );

                int labelIndex =
                        cursor.getColumnIndex(
                                ContactsContract.CommonDataKinds.Phone
                                        .LABEL
                        );

                while (cursor.moveToNext()) {
                    long contactId =
                            idIndex < 0
                                    ? -1L
                                    : cursor.getLong(
                                            idIndex
                                    );

                    ContactRow row =
                            contacts.get(contactId);

                    if (row == null) {
                        continue;
                    }

                    String number =
                            numberIndex < 0
                                    ? ""
                                    : safe(
                                            cursor.getString(
                                                    numberIndex
                                            )
                                    );

                    String normalized =
                            JarvisCallerIdentity
                                    .normalize(number);

                    if (normalized.isEmpty()) {
                        continue;
                    }

                    boolean exists = false;
                    for (PhoneEntry item : row.numbers) {
                        if (normalized.equals(
                                item.normalized
                        )) {
                            exists = true;
                            break;
                        }
                    }

                    if (exists) {
                        continue;
                    }

                    int type =
                            typeIndex < 0
                                    ? ContactsContract
                                    .CommonDataKinds.Phone
                                    .TYPE_OTHER
                                    : cursor.getInt(
                                            typeIndex
                                    );

                    String customLabel =
                            labelIndex < 0
                                    ? ""
                                    : safe(
                                            cursor.getString(
                                                    labelIndex
                                            )
                                    );

                    CharSequence labelText =
                            ContactsContract
                                    .CommonDataKinds.Phone
                                    .getTypeLabel(
                                            getResources(),
                                            type,
                                            customLabel
                                    );

                    row.numbers.add(
                            new PhoneEntry(
                                    number,
                                    normalized,
                                    labelText == null
                                            ? ""
                                            : labelText.toString()
                            )
                    );
                }
            }

        } catch (SecurityException ignored) {
        }

        List<ContactRow> rows =
                new ArrayList<>();

        for (ContactRow row : contacts.values()) {
            if (row.numbers.isEmpty()) {
                continue;
            }

            if (!cleanFilter.isEmpty()
                    && isMostlyDigits(
                    cleanFilter
            )) {
                String needle =
                        JarvisCallerIdentity
                                .normalize(
                                        cleanFilter
                                );

                boolean numberMatch = false;

                for (PhoneEntry phone : row.numbers) {
                    if (phone.normalized.contains(
                            needle
                    )) {
                        numberMatch = true;
                        break;
                    }
                }

                if (!numberMatch) {
                    continue;
                }
            }

            rows.add(row);
        }

        Collections.sort(
                rows,
                Comparator.comparing(
                        row -> row.name.toLowerCase(
                                Locale.getDefault()
                        )
                )
        );

        if (rows.size() > limit) {
            return new ArrayList<>(
                    rows.subList(0, limit)
            );
        }

        return rows;
    }

    private Map<Long, ContactRow> loadVisibleContactBases(
            String filter
    ) {
        Map<Long, ContactRow> out =
                new LinkedHashMap<>();

        Uri uri;

        if (!filter.isEmpty()
                && !isMostlyDigits(filter)) {
            uri =
                    Uri.withAppendedPath(
                            ContactsContract.Contacts
                                    .CONTENT_FILTER_URI,
                            Uri.encode(filter)
                    );
        } else {
            uri =
                    ContactsContract.Contacts
                            .CONTENT_URI;
        }

        String[] projection =
                new String[]{
                        ContactsContract.Contacts._ID,
                        ContactsContract.Contacts
                                .DISPLAY_NAME_PRIMARY,
                        ContactsContract.Contacts
                                .PHOTO_THUMBNAIL_URI,
                        ContactsContract.Contacts
                                .LOOKUP_KEY,
                        ContactsContract.Contacts
                                .HAS_PHONE_NUMBER,
                        ContactsContract.Contacts
                                .IN_VISIBLE_GROUP,
                        ContactsContract.Contacts
                                .IN_DEFAULT_DIRECTORY
                };

        String selection =
                ContactsContract.Contacts
                        .HAS_PHONE_NUMBER
                        + "=1 AND "
                        + ContactsContract.Contacts
                        .IN_VISIBLE_GROUP
                        + "=1 AND "
                        + ContactsContract.Contacts
                        .IN_DEFAULT_DIRECTORY
                        + "=1";

        try (
                Cursor cursor =
                        getContentResolver().query(
                                uri,
                                projection,
                                selection,
                                null,
                                ContactsContract.Contacts
                                        .DISPLAY_NAME_PRIMARY
                                        + " COLLATE NOCASE ASC"
                        )
        ) {
            if (cursor == null) {
                return out;
            }

            int idIndex =
                    cursor.getColumnIndex(
                            ContactsContract.Contacts._ID
                    );

            int nameIndex =
                    cursor.getColumnIndex(
                            ContactsContract.Contacts
                                    .DISPLAY_NAME_PRIMARY
                    );

            int photoIndex =
                    cursor.getColumnIndex(
                            ContactsContract.Contacts
                                    .PHOTO_THUMBNAIL_URI
                    );

            int lookupIndex =
                    cursor.getColumnIndex(
                            ContactsContract.Contacts
                                    .LOOKUP_KEY
                    );

            while (cursor.moveToNext()) {
                long id =
                        idIndex < 0
                                ? -1L
                                : cursor.getLong(
                                        idIndex
                                );

                if (id <= 0) {
                    continue;
                }

                String name =
                        nameIndex < 0
                                ? ""
                                : safe(
                                        cursor.getString(
                                                nameIndex
                                        )
                                );

                String photoUri =
                        photoIndex < 0
                                ? ""
                                : safe(
                                        cursor.getString(
                                                photoIndex
                                        )
                                );

                String lookupKey =
                        lookupIndex < 0
                                ? ""
                                : safe(
                                        cursor.getString(
                                                lookupIndex
                                        )
                                );

                out.put(
                        id,
                        new ContactRow(
                                id,
                                name.isEmpty()
                                        ? "Unnamed contact"
                                        : name,
                                photoUri,
                                lookupKey
                        )
                );
            }

        } catch (SecurityException ignored) {
        }

        return out;
    }

    private LinearLayout contactCard(
            ContactRow row,
            boolean showManage
    ) {
        LinearLayout card = rowContainer();

        card.addView(
                contactAvatar(row)
        );

        String subtitle =
                row.numbers.size() == 1
                        ? displayPhone(
                                row.numbers.get(0)
                        )
                        : row.numbers.size()
                        + " phone numbers";

        LinearLayout text =
                rowTextBlock(
                        row.name,
                        subtitle
                );

        card.addView(
                text,
                new LinearLayout.LayoutParams(
                        0,
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        1f
                )
        );

        if (showManage) {
            TextView manage =
                    chip(
                            "MANAGE",
                            CARD_2,
                            TEXT
                    );

            manage.setOnClickListener(
                    v -> openContact(row)
            );

            card.addView(manage);
            card.addView(space(dp(6)));
        }

        TextView call =
                chip(
                        "CALL",
                        GREEN,
                        Color.WHITE
                );

        call.setOnClickListener(
                v -> chooseNumberAndCall(row)
        );

        card.addView(call);

        return card;
    }

    private String displayPhone(
            PhoneEntry entry
    ) {
        String formatted =
                JarvisCallerIdentity
                        .displayNumber(
                                entry.raw
                        );

        if (entry.label.isEmpty()) {
            return formatted;
        }

        return entry.label
                + "  \u2022  "
                + formatted;
    }

    private void chooseNumberAndCall(
            ContactRow row
    ) {
        if (row.numbers.isEmpty()) {
            return;
        }

        if (row.numbers.size() == 1) {
            placeCall(
                    row.numbers.get(0).raw
            );
            return;
        }

        String[] labels =
                new String[row.numbers.size()];

        for (int i = 0;
             i < row.numbers.size();
             i++) {
            labels[i] =
                    displayPhone(
                            row.numbers.get(i)
                    );
        }

        new AlertDialog.Builder(this)
                .setTitle(row.name)
                .setItems(
                        labels,
                        (dialog, which) ->
                                placeCall(
                                        row.numbers
                                                .get(which)
                                                .raw
                                )
                )
                .setNegativeButton(
                        "Cancel",
                        null
                )
                .show();
    }

    private View contactAvatar(
            ContactRow row
    ) {
        FrameLayout frame =
                new FrameLayout(this);

        frame.setBackground(
                circle(CARD_2)
        );
        frame.setClipToOutline(true);

        LinearLayout.LayoutParams lp =
                new LinearLayout.LayoutParams(
                        dp(54),
                        dp(54)
                );
        frame.setLayoutParams(lp);

        Bitmap bitmap =
                JarvisCallerIdentity.loadPhoto(
                        this,
                        row.photoUri
                );

        if (bitmap != null) {
            ImageView image =
                    new ImageView(this);

            image.setImageBitmap(bitmap);
            image.setScaleType(
                    ImageView.ScaleType.CENTER_CROP
            );
            image.setClipToOutline(true);

            frame.addView(
                    image,
                    new FrameLayout.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.MATCH_PARENT
                    )
            );

        } else {
            TextView initial =
                    new TextView(this);

            initial.setText(
                    row.name.isEmpty()
                            ? "?"
                            : row.name.substring(0, 1)
                            .toUpperCase()
            );
            initial.setTextColor(TEXT);
            initial.setTextSize(20f);
            initial.setTypeface(
                    Typeface.DEFAULT_BOLD
            );
            initial.setGravity(Gravity.CENTER);

            frame.addView(
                    initial,
                    new FrameLayout.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.MATCH_PARENT
                    )
            );
        }

        return frame;
    }

    private List<RecentRow> loadRecents(
            int limit
    ) {
        List<RecentRow> out =
                new ArrayList<>();

        String[] projection =
                new String[]{
                        CallLog.Calls.NUMBER,
                        CallLog.Calls.CACHED_NAME,
                        CallLog.Calls.TYPE,
                        CallLog.Calls.DATE
                };

        try (
                Cursor cursor =
                        getContentResolver().query(
                                CallLog.Calls.CONTENT_URI,
                                projection,
                                null,
                                null,
                                CallLog.Calls.DATE
                                        + " DESC"
                        )
        ) {
            if (cursor == null) {
                return out;
            }

            int numberIndex =
                    cursor.getColumnIndex(
                            CallLog.Calls.NUMBER
                    );

            int nameIndex =
                    cursor.getColumnIndex(
                            CallLog.Calls.CACHED_NAME
                    );

            int typeIndex =
                    cursor.getColumnIndex(
                            CallLog.Calls.TYPE
                    );

            int dateIndex =
                    cursor.getColumnIndex(
                            CallLog.Calls.DATE
                    );

            while (cursor.moveToNext()
                    && out.size() < limit) {

                String number =
                        numberIndex < 0
                                ? ""
                                : safe(
                                        cursor.getString(
                                                numberIndex
                                        )
                                );

                String name =
                        nameIndex < 0
                                ? ""
                                : safe(
                                        cursor.getString(
                                                nameIndex
                                        )
                                );

                int type =
                        typeIndex < 0
                                ? 0
                                : cursor.getInt(
                                        typeIndex
                                );

                long date =
                        dateIndex < 0
                                ? 0L
                                : cursor.getLong(
                                        dateIndex
                                );

                JarvisCallerIdentity.Result identity =
                        JarvisCallerIdentity.resolve(
                                this,
                                number,
                                name
                        );

                out.add(
                        new RecentRow(
                                identity.displayName,
                                number,
                                type,
                                date
                        )
                );
            }

        } catch (SecurityException ignored) {
        }

        return out;
    }

    private LinearLayout recentRow(
            RecentRow row
    ) {
        LinearLayout card = rowContainer();

        TextView avatar =
                avatarInitial(row.name);

        LinearLayout text =
                rowTextBlock(
                        row.name,
                        recentSubtitle(row)
                );

        TextView call =
                chip(
                        "CALL",
                        GREEN,
                        Color.WHITE
                );

        call.setOnClickListener(
                v -> placeCall(row.number)
        );

        card.addView(avatar);
        card.addView(
                text,
                new LinearLayout.LayoutParams(
                        0,
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        1f
                )
        );
        card.addView(call);

        return card;
    }

    private void placeCall(String number) {
        String clean =
                number == null
                        ? ""
                        : number.trim();

        if (clean.isEmpty()) {
            Toast.makeText(
                    this,
                    "Enter a phone number",
                    Toast.LENGTH_SHORT
            ).show();
            return;
        }

        if (checkSelfPermission(
                Manifest.permission.CALL_PHONE
        ) != PackageManager.PERMISSION_GRANTED) {

            pendingNumber = clean;

            requestPermissions(
                    new String[]{
                            Manifest.permission.CALL_PHONE
                    },
                    REQUEST_CALL_PHONE
            );
            return;
        }

        JarvisPhoneActions.Result result =
                JarvisPhoneActions
                        .placeCarrierCall(
                                this,
                                clean
                        );

        if (!result.ok) {
            Toast.makeText(
                    this,
                    result.message,
                    Toast.LENGTH_LONG
            ).show();
            return;
        }

        if (addCallMode) {
            finish();
        }
    }

    private void addContact() {
        Intent intent =
                new Intent(
                        Intent.ACTION_INSERT,
                        ContactsContract.Contacts
                                .CONTENT_URI
                );
        intent.setType(
                ContactsContract.Contacts
                        .CONTENT_TYPE
        );
        startActivity(intent);
    }

    private void openContact(
            ContactRow row
    ) {
        Uri uri;

        if (!row.lookupKey.isEmpty()) {
            uri =
                    ContactsContract.Contacts
                            .getLookupUri(
                                    row.contactId,
                                    row.lookupKey
                            );
        } else {
            uri =
                    Uri.withAppendedPath(
                            ContactsContract.Contacts
                                    .CONTENT_URI,
                            Long.toString(
                                    row.contactId
                            )
                    );
        }

        startActivity(
                new Intent(
                        Intent.ACTION_VIEW,
                        uri
                )
        );
    }

    private void deleteOne(EditText field) {
        int start = field.getSelectionStart();
        int end = field.getSelectionEnd();

        if (start < 0 || end < 0) {
            return;
        }

        if (start != end) {
            field.getText().delete(
                    Math.min(start, end),
                    Math.max(start, end)
            );
        } else if (start > 0) {
            field.getText().delete(
                    start - 1,
                    start
            );
        }
    }

    @Override
    public void onRequestPermissionsResult(
            int requestCode,
            String[] permissions,
            int[] grantResults
    ) {
        super.onRequestPermissionsResult(
                requestCode,
                permissions,
                grantResults
        );

        boolean granted =
                grantResults.length > 0
                        && grantResults[0]
                        == PackageManager.PERMISSION_GRANTED;

        if (!granted) {
            Toast.makeText(
                    this,
                    "Permission denied",
                    Toast.LENGTH_SHORT
            ).show();
            return;
        }

        if (requestCode
                == REQUEST_CALL_PHONE) {
            String number = pendingNumber;
            pendingNumber = "";
            placeCall(number);
            return;
        }

        if (requestCode
                == REQUEST_CONTACTS) {
            showContacts();
            return;
        }

        if (requestCode
                == REQUEST_CALL_LOG) {
            showRecents();
        }
    }

    private void header(
            String title,
            String subtitle
    ) {
        content.addView(
                headingText(title)
        );
        content.addView(
                smallText(subtitle),
                fullWidthWrap(
                        dp(4),
                        dp(10)
                )
        );
    }

    private TextView headingText(
            String title
    ) {
        TextView heading =
                new TextView(this);

        heading.setText(title);
        heading.setTextColor(TEXT);
        heading.setTextSize(21f);
        heading.setTypeface(
                Typeface.DEFAULT_BOLD
        );

        return heading;
    }

    private void permissionCard(
            String title,
            String message,
            View.OnClickListener listener
    ) {
        LinearLayout card =
                new LinearLayout(this);
        card.setOrientation(
                LinearLayout.VERTICAL
        );
        card.setPadding(
                dp(18),
                dp(18),
                dp(18),
                dp(18)
        );
        card.setBackground(
                rounded(CARD, dp(18))
        );

        card.addView(
                headingText(title)
        );

        card.addView(
                smallText(message),
                fullWidthWrap(
                        dp(7),
                        dp(14)
                )
        );

        TextView button =
                chip(
                        "ALLOW",
                        ORANGE,
                        Color.WHITE
                );

        button.setOnClickListener(
                listener
        );
        card.addView(button);

        content.addView(
                card,
                fullWidthWrap(
                        dp(12),
                        0
                )
        );
    }

    private void emptyCard(String message) {
        TextView card =
                smallText(message);

        card.setGravity(Gravity.CENTER);
        card.setPadding(
                dp(16),
                dp(28),
                dp(16),
                dp(28)
        );
        card.setBackground(
                rounded(CARD, dp(18))
        );

        content.addView(
                card,
                fullWidthWrap(
                        dp(10),
                        0
                )
        );
    }

    private TextView navItem(
            String label,
            View.OnClickListener listener
    ) {
        TextView view =
                new TextView(this);

        view.setText(label);
        view.setTextSize(14f);
        view.setGravity(Gravity.CENTER);
        view.setPadding(
                dp(8),
                dp(11),
                dp(8),
                dp(11)
        );
        view.setOnClickListener(listener);
        return view;
    }

    private void selectTab(
            TextView selected
    ) {
        TextView[] tabs =
                new TextView[]{
                        tabRecents,
                        tabContacts,
                        tabKeypad
                };

        for (TextView tab : tabs) {
            if (tab == null) {
                continue;
            }

            boolean active =
                    tab == selected;

            tab.setTextColor(
                    active
                            ? ORANGE
                            : MUTED
            );

            tab.setTypeface(
                    active
                            ? Typeface.DEFAULT_BOLD
                            : Typeface.DEFAULT
            );
        }
    }

    private LinearLayout rowContainer() {
        LinearLayout row =
                new LinearLayout(this);

        row.setOrientation(
                LinearLayout.HORIZONTAL
        );
        row.setGravity(
                Gravity.CENTER_VERTICAL
        );
        row.setPadding(
                dp(13),
                dp(12),
                dp(13),
                dp(12)
        );
        row.setBackground(
                rounded(CARD, dp(18))
        );

        return row;
    }

    private LinearLayout rowTextBlock(
            String title,
            String subtitle
    ) {
        LinearLayout block =
                new LinearLayout(this);
        block.setOrientation(
                LinearLayout.VERTICAL
        );
        block.setPadding(
                dp(12),
                0,
                dp(8),
                0
        );

        TextView titleView =
                new TextView(this);
        titleView.setText(
                title == null
                        || title.trim().isEmpty()
                        ? "Unknown"
                        : title
        );
        titleView.setTextColor(TEXT);
        titleView.setTextSize(16f);
        titleView.setTypeface(
                Typeface.DEFAULT_BOLD
        );

        TextView subtitleView =
                smallText(subtitle);

        block.addView(titleView);
        block.addView(subtitleView);

        return block;
    }

    private TextView avatarInitial(
            String name
    ) {
        TextView avatar =
                new TextView(this);

        String value =
                name == null
                        || name.trim().isEmpty()
                        ? "?"
                        : name.trim()
                        .substring(0, 1)
                        .toUpperCase();

        avatar.setText(value);
        avatar.setTextColor(TEXT);
        avatar.setTextSize(19f);
        avatar.setTypeface(
                Typeface.DEFAULT_BOLD
        );
        avatar.setGravity(Gravity.CENTER);
        avatar.setBackground(
                circle(CARD_2)
        );
        avatar.setLayoutParams(
                new LinearLayout.LayoutParams(
                        dp(52),
                        dp(52)
                )
        );

        return avatar;
    }

    private TextView chip(
            String label,
            int background,
            int foreground
    ) {
        TextView chip =
                new TextView(this);

        chip.setText(label);
        chip.setTextColor(foreground);
        chip.setTextSize(11f);
        chip.setTypeface(
                Typeface.DEFAULT_BOLD
        );
        chip.setGravity(Gravity.CENTER);
        chip.setPadding(
                dp(13),
                dp(9),
                dp(13),
                dp(9)
        );
        chip.setBackground(
                rounded(
                        background,
                        dp(18)
                )
        );

        return chip;
    }

    private TextView keypadButton(
            String digit
    ) {
        TextView button =
                new TextView(this);

        button.setTag(digit);
        button.setText(digit);
        button.setTextColor(TEXT);
        button.setTextSize(29f);
        button.setTypeface(
                Typeface.DEFAULT
        );
        button.setGravity(Gravity.CENTER);
        button.setBackground(
                circle(CARD_2)
        );

        return button;
    }

    private TextView smallText(
            String value
    ) {
        TextView view =
                new TextView(this);

        view.setText(value);
        view.setTextColor(MUTED);
        view.setTextSize(13f);

        return view;
    }

    private String recentSubtitle(
            RecentRow row
    ) {
        String type;

        switch (row.type) {
            case CallLog.Calls.INCOMING_TYPE:
                type = "Incoming";
                break;

            case CallLog.Calls.OUTGOING_TYPE:
                type = "Outgoing";
                break;

            case CallLog.Calls.MISSED_TYPE:
                type = "Missed";
                break;

            case CallLog.Calls.REJECTED_TYPE:
                type = "Rejected";
                break;

            default:
                type = "Call";
                break;
        }

        String when =
                row.date <= 0
                        ? ""
                        : DateFormat
                        .getDateTimeInstance(
                                DateFormat.SHORT,
                                DateFormat.SHORT,
                                Locale.getDefault()
                        )
                        .format(
                                new Date(row.date)
                        );

        return type
                + (
                when.isEmpty()
                        ? ""
                        : "  \u2022  " + when
        )
                + "\n"
                + JarvisCallerIdentity
                .displayNumber(row.number);
    }

    private String numberFromIntent() {
        if (getIntent() == null
                || getIntent().getData() == null) {
            return "";
        }

        Uri uri =
                getIntent().getData();

        if (!"tel".equalsIgnoreCase(
                uri.getScheme()
        )) {
            return "";
        }

        String number =
                uri.getSchemeSpecificPart();

        return number == null
                ? ""
                : number.trim();
    }

    private static boolean isMostlyDigits(
            String value
    ) {
        String clean =
                value == null
                        ? ""
                        : value.trim();

        if (clean.isEmpty()) {
            return false;
        }

        int digits = 0;

        for (int i = 0;
             i < clean.length();
             i++) {
            if (Character.isDigit(
                    clean.charAt(i)
            )) {
                digits++;
            }
        }

        return digits
                >= Math.max(
                1,
                clean.length() - 2
        );
    }

    private static String safe(
            String value
    ) {
        return value == null
                ? ""
                : value.trim();
    }

    private void clearContent() {
        content.removeAllViews();
    }

    private View space(int width) {
        Space space = new Space(this);
        space.setLayoutParams(
                new LinearLayout.LayoutParams(
                        width,
                        1
                )
        );
        return space;
    }

    private GradientDrawable rounded(
            int color,
            int radius
    ) {
        GradientDrawable drawable =
                new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(radius);
        return drawable;
    }

    private GradientDrawable circle(
            int color
    ) {
        GradientDrawable drawable =
                new GradientDrawable();
        drawable.setShape(
                GradientDrawable.OVAL
        );
        drawable.setColor(color);
        return drawable;
    }

    private LinearLayout.LayoutParams navWeight() {
        return new LinearLayout.LayoutParams(
                0,
                ViewGroup.LayoutParams.WRAP_CONTENT,
                1f
        );
    }

    private LinearLayout.LayoutParams fullWidthWrap(
            int top,
            int bottom
    ) {
        LinearLayout.LayoutParams params =
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                );

        params.topMargin = top;
        params.bottomMargin = bottom;
        return params;
    }

    private int dp(int value) {
        return Math.round(
                value
                        * getResources()
                        .getDisplayMetrics()
                        .density
        );
    }

    private static final class PhoneEntry {
        final String raw;
        final String normalized;
        final String label;

        PhoneEntry(
                String raw,
                String normalized,
                String label
        ) {
            this.raw = raw;
            this.normalized = normalized;
            this.label = label;
        }
    }

    private static final class ContactRow {
        final long contactId;
        final String name;
        final String photoUri;
        final String lookupKey;
        final List<PhoneEntry> numbers =
                new ArrayList<>();

        ContactRow(
                long contactId,
                String name,
                String photoUri,
                String lookupKey
        ) {
            this.contactId = contactId;
            this.name = name;
            this.photoUri = photoUri;
            this.lookupKey = lookupKey;
        }
    }

    private static final class RecentRow {
        final String name;
        final String number;
        final int type;
        final long date;

        RecentRow(
                String name,
                String number,
                int type,
                long date
        ) {
            this.name = name;
            this.number = number;
            this.type = type;
            this.date = date;
        }
    }
}
