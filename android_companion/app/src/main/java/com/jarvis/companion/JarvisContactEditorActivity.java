package com.jarvis.companion;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.provider.ContactsContract;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public final class JarvisContactEditorActivity
        extends Activity {

    public static final String EXTRA_CONTACT_ID =
            "jarvis_contact_id";

    private static final int REQUEST_WRITE_CONTACTS =
            4201;

    private static final int REQUEST_PICK_PHOTO =
            4202;

    private static final int BG =
            Color.rgb(4, 9, 16);

    private static final int CARD =
            Color.rgb(15, 23, 34);

    private static final int CARD_2 =
            Color.rgb(23, 34, 48);

    private static final int TEXT =
            Color.rgb(248, 250, 252);

    private static final int MUTED =
            Color.rgb(148, 163, 184);

    private static final int ORANGE =
            Color.rgb(255, 153, 61);

    private static final int GREEN =
            Color.rgb(43, 190, 102);

    private static final int RED =
            Color.rgb(239, 68, 68);

    private long contactId = -1L;
    private JarvisContactStore.ContactData original;

    private ImageView photoView;
    private TextView initialView;
    private EditText nameField;
    private LinearLayout phonesContainer;
    private CheckBox favoriteCheck;
    private Spinner accountSpinner;
    private TextView accountReadOnly;
    private LinearLayout groupsContainer;

    private final List<PhoneEditorRow> phoneRows =
            new ArrayList<>();

    private final List<GroupCheckRow> groupRows =
            new ArrayList<>();

    private List<JarvisContactStore.AccountInfo>
            accounts =
            new ArrayList<>();

    private List<JarvisContactStore.GroupInfo>
            groups =
            new ArrayList<>();

    private byte[] newPhotoBytes = null;
    private boolean removePhoto = false;

    @Override
    protected void onCreate(
            Bundle savedInstanceState
    ) {
        super.onCreate(savedInstanceState);

        contactId =
                getIntent() == null
                        ? -1L
                        : getIntent()
                        .getLongExtra(
                                EXTRA_CONTACT_ID,
                                -1L
                        );

        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);

        if (checkSelfPermission(
                Manifest.permission.READ_CONTACTS
        ) != PackageManager.PERMISSION_GRANTED
                || checkSelfPermission(
                Manifest.permission.WRITE_CONTACTS
        ) != PackageManager.PERMISSION_GRANTED) {

            requestPermissions(
                    new String[]{
                            Manifest.permission.READ_CONTACTS,
                            Manifest.permission.WRITE_CONTACTS
                    },
                    REQUEST_WRITE_CONTACTS
            );
        }

        loadModel();
        setContentView(buildUi());
        bindModel();
    }

    private void loadModel() {
        accounts =
                JarvisContactStore
                        .loadWritableAccountCandidates(
                                this
                        );

        groups =
                JarvisContactStore
                        .loadGroups(this);

        if (contactId > 0L) {
            original =
                    JarvisContactStore.loadContact(
                            this,
                            contactId
                    );
        }
    }

    private View buildUi() {
        ScrollView scroll =
                new ScrollView(this);

        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BG);

        LinearLayout root =
                new LinearLayout(this);

        root.setOrientation(
                LinearLayout.VERTICAL
        );

        root.setPadding(
                dp(20),
                dp(24),
                dp(20),
                dp(34)
        );

        scroll.addView(
                root,
                new ScrollView.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                )
        );

        TextView brand =
                new TextView(this);

        brand.setText("J A R V I S");
        brand.setTextColor(ORANGE);
        brand.setTextSize(12f);
        brand.setTypeface(
                Typeface.DEFAULT_BOLD
        );
        brand.setLetterSpacing(0.14f);

        root.addView(brand);

        TextView title =
                new TextView(this);

        title.setText(
                contactId > 0L
                        ? "Contact"
                        : "New contact"
        );

        title.setTextColor(TEXT);
        title.setTextSize(30f);
        title.setTypeface(
                Typeface.DEFAULT_BOLD
        );

        root.addView(
                title,
                margins(0, dp(4), 0, dp(20))
        );

        FrameLayout avatar =
                new FrameLayout(this);

        avatar.setBackground(
                circle(CARD_2)
        );
        avatar.setClipToOutline(true);

        LinearLayout.LayoutParams avatarParams =
                new LinearLayout.LayoutParams(
                        dp(116),
                        dp(116)
                );

        avatarParams.gravity =
                Gravity.CENTER_HORIZONTAL;

        root.addView(
                avatar,
                avatarParams
        );

        photoView =
                new ImageView(this);

        photoView.setScaleType(
                ImageView.ScaleType.CENTER_CROP
        );

        avatar.addView(
                photoView,
                new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                )
        );

        initialView =
                new TextView(this);

        initialView.setTextColor(TEXT);
        initialView.setTextSize(38f);
        initialView.setTypeface(
                Typeface.DEFAULT_BOLD
        );
        initialView.setGravity(Gravity.CENTER);

        avatar.addView(
                initialView,
                new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                )
        );

        LinearLayout photoButtons =
                new LinearLayout(this);

        photoButtons.setOrientation(
                LinearLayout.HORIZONTAL
        );

        photoButtons.setGravity(
                Gravity.CENTER
        );

        TextView choosePhoto =
                chip(
                        "CHOOSE PHOTO",
                        CARD_2,
                        TEXT
                );

        choosePhoto.setOnClickListener(
                v -> pickPhoto()
        );

        TextView removePhotoButton =
                chip(
                        "REMOVE",
                        CARD_2,
                        MUTED
                );

        removePhotoButton.setOnClickListener(
                v -> {
                    newPhotoBytes = null;
                    removePhoto = true;
                    showPhoto(null);
                }
        );

        photoButtons.addView(choosePhoto);
        photoButtons.addView(space(dp(8)));
        photoButtons.addView(
                removePhotoButton
        );

        root.addView(
                photoButtons,
                margins(0, dp(12), 0, dp(22))
        );

        root.addView(sectionLabel("Name"));

        nameField =
                input("Full name");

        root.addView(
                nameField,
                margins(0, dp(7), 0, dp(18))
        );

        LinearLayout phonesHeader =
                new LinearLayout(this);

        phonesHeader.setOrientation(
                LinearLayout.HORIZONTAL
        );

        phonesHeader.setGravity(
                Gravity.CENTER_VERTICAL
        );

        TextView phonesTitle =
                sectionLabel("Phone numbers");

        TextView addNumber =
                chip(
                        "+ NUMBER",
                        CARD_2,
                        TEXT
                );

        addNumber.setOnClickListener(
                v -> addPhoneRow(
                        -1L,
                        "",
                        ContactsContract
                                .CommonDataKinds
                                .Phone.TYPE_MOBILE
                )
        );

        phonesHeader.addView(
                phonesTitle,
                new LinearLayout.LayoutParams(
                        0,
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        1f
                )
        );

        phonesHeader.addView(addNumber);
        root.addView(phonesHeader);

        phonesContainer =
                new LinearLayout(this);

        phonesContainer.setOrientation(
                LinearLayout.VERTICAL
        );

        root.addView(
                phonesContainer,
                margins(0, dp(7), 0, dp(18))
        );

        favoriteCheck =
                new CheckBox(this);

        favoriteCheck.setText("Favorite");
        favoriteCheck.setTextColor(TEXT);
        favoriteCheck.setTextSize(16f);
        favoriteCheck.setButtonTintList(
                android.content.res.ColorStateList
                        .valueOf(ORANGE)
        );

        root.addView(
                favoriteCheck,
                margins(0, 0, 0, dp(18))
        );

        root.addView(
                sectionLabel("Account")
        );

        if (contactId <= 0L) {
            accountSpinner =
                    new Spinner(this);

            root.addView(
                    accountSpinner,
                    margins(
                            0,
                            dp(7),
                            0,
                            dp(18)
                    )
            );
        } else {
            accountReadOnly =
                    smallText("");

            accountReadOnly.setPadding(
                    dp(14),
                    dp(13),
                    dp(14),
                    dp(13)
            );

            accountReadOnly.setBackground(
                    rounded(
                            CARD,
                            dp(16)
                    )
            );

            root.addView(
                    accountReadOnly,
                    margins(
                            0,
                            dp(7),
                            0,
                            dp(18)
                    )
            );
        }

        LinearLayout groupsHeader =
                new LinearLayout(this);

        groupsHeader.setOrientation(
                LinearLayout.HORIZONTAL
        );

        groupsHeader.setGravity(
                Gravity.CENTER_VERTICAL
        );

        TextView groupsTitle =
                sectionLabel(
                        "Groups / categories"
                );

        TextView newGroup =
                chip(
                        "+ NEW GROUP",
                        CARD_2,
                        TEXT
                );

        newGroup.setOnClickListener(
                v -> createGroupDialog()
        );

        groupsHeader.addView(
                groupsTitle,
                new LinearLayout.LayoutParams(
                        0,
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        1f
                )
        );

        groupsHeader.addView(newGroup);

        root.addView(groupsHeader);

        groupsContainer =
                new LinearLayout(this);

        groupsContainer.setOrientation(
                LinearLayout.VERTICAL
        );

        root.addView(
                groupsContainer,
                margins(0, dp(7), 0, dp(22))
        );

        LinearLayout actions =
                new LinearLayout(this);

        actions.setOrientation(
                LinearLayout.HORIZONTAL
        );

        actions.setGravity(Gravity.CENTER);

        TextView cancel =
                chip(
                        "CANCEL",
                        CARD_2,
                        TEXT
                );

        cancel.setOnClickListener(
                v -> finish()
        );

        TextView save =
                chip(
                        "SAVE",
                        GREEN,
                        Color.WHITE
                );

        save.setOnClickListener(
                v -> saveContact()
        );

        actions.addView(cancel);
        actions.addView(space(dp(10)));
        actions.addView(save);

        root.addView(actions);

        if (contactId > 0L) {
            TextView delete =
                    chip(
                            "DELETE CONTACT",
                            RED,
                            Color.WHITE
                    );

            delete.setOnClickListener(
                    v -> confirmDelete()
            );

            root.addView(
                    delete,
                    margins(
                            0,
                            dp(18),
                            0,
                            0
                    )
            );
        }

        return scroll;
    }

    private void bindModel() {
        if (original != null) {
            nameField.setText(
                    original.name
            );

            favoriteCheck.setChecked(
                    original.starred
            );

            Bitmap photo =
                    JarvisContactStore
                            .loadContactPhoto(
                                    this,
                                    original.contactId,
                                    original.photoUri
                            );

            showPhoto(photo);

            if (accountReadOnly != null) {
                accountReadOnly.setText(
                        original.account == null
                                ? "Device"
                                : original.account.label()
                );
            }

            for (
                    JarvisContactStore.PhoneData phone
                    : original.phones
            ) {
                addPhoneRow(
                        phone.dataId,
                        phone.number,
                        phone.type
                );
            }

            if (phoneRows.isEmpty()) {
                addPhoneRow(
                        -1L,
                        "",
                        ContactsContract
                                .CommonDataKinds
                                .Phone.TYPE_MOBILE
                );
            }

        } else {
            showPhoto(null);

            if (accountSpinner != null) {
                List<String> labels =
                        new ArrayList<>();

                for (
                        JarvisContactStore.AccountInfo account
                        : accounts
                ) {
                    labels.add(
                            account.label()
                    );
                }

                ArrayAdapter<String> adapter =
                        new ArrayAdapter<String>(
                                this,
                                android.R.layout
                                        .simple_spinner_item,
                                labels
                        ) {
                    @Override
                    public View getView(
                            int position,
                            View convertView,
                            ViewGroup parent
                    ) {
                        TextView view =
                                (TextView) super.getView(
                                        position,
                                        convertView,
                                        parent
                                );

                        styleAccountRow(
                                view,
                                false
                        );

                        return view;
                    }

                    @Override
                    public View getDropDownView(
                            int position,
                            View convertView,
                            ViewGroup parent
                    ) {
                        TextView view =
                                (TextView) super
                                        .getDropDownView(
                                                position,
                                                convertView,
                                                parent
                                        );

                        styleAccountRow(
                                view,
                                true
                        );

                        return view;
                    }
                };

                accountSpinner.setAdapter(
                        adapter
                );

                accountSpinner
                        .setOnItemSelectedListener(
                                new android.widget
                                        .AdapterView
                                        .OnItemSelectedListener() {

                    @Override
                    public void onItemSelected(
                            android.widget.AdapterView<?> parent,
                            View view,
                            int position,
                            long id
                    ) {
                        rebuildGroups();
                    }

                    @Override
                    public void onNothingSelected(
                            android.widget.AdapterView<?> parent
                    ) {
                    }
                });
            }

            addPhoneRow(
                    -1L,
                    "",
                    ContactsContract
                            .CommonDataKinds
                            .Phone.TYPE_MOBILE
            );
        }

        nameField.addTextChangedListener(
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
                updateInitial();
            }

            @Override
            public void afterTextChanged(
                    android.text.Editable s
            ) {
            }
        });

        rebuildGroups();
        updateInitial();
    }

    private void rebuildGroups() {
        groupsContainer.removeAllViews();
        groupRows.clear();

        JarvisContactStore.AccountInfo account =
                currentAccount();

        int visibleCount = 0;

        for (
                JarvisContactStore.GroupInfo group
                : groups
        ) {
            boolean alreadyMember =
                    original != null
                            && original.groupIds.contains(
                            group.id
                    );

            if (!group.matches(account)
                    && !alreadyMember) {
                continue;
            }

            LinearLayout groupLine =
                    new LinearLayout(this);

            groupLine.setOrientation(
                    LinearLayout.HORIZONTAL
            );

            groupLine.setGravity(
                    Gravity.CENTER_VERTICAL
            );

            CheckBox check =
                    new CheckBox(this);

            check.setText(group.title);
            check.setTextColor(TEXT);
            check.setTextSize(15f);
            check.setButtonTintList(
                    android.content.res.ColorStateList
                            .valueOf(ORANGE)
            );

            if (original != null
                    && original.groupIds.contains(
                    group.id
            )) {
                check.setChecked(true);
            }

            TextView deleteGroup =
                    chip(
                            "DELETE",
                            CARD_2,
                            RED
                    );

            deleteGroup.setOnClickListener(
                    v -> confirmDeleteGroup(
                            group
                    )
            );

            groupLine.addView(
                    check,
                    new LinearLayout.LayoutParams(
                            0,
                            ViewGroup.LayoutParams.WRAP_CONTENT,
                            1f
                    )
            );

            groupLine.addView(
                    deleteGroup
            );

            groupsContainer.addView(
                    groupLine
            );

            groupRows.add(
                    new GroupCheckRow(
                            group,
                            check
                    )
            );

            visibleCount++;
        }

        if (visibleCount == 0) {
            groupsContainer.addView(
                    smallText(
                            "No contact groups are available for this account."
                    )
            );
        }
    }

    private void addPhoneRow(
            long dataId,
            String number,
            int type
    ) {
        LinearLayout row =
                new LinearLayout(this);

        row.setOrientation(
                LinearLayout.HORIZONTAL
        );

        row.setGravity(
                Gravity.CENTER_VERTICAL
        );

        EditText field =
                input("Phone number");

        field.setInputType(
                android.text.InputType
                        .TYPE_CLASS_PHONE
        );

        field.setText(number);

        TextView remove =
                chip(
                        "\u2212",
                        CARD_2,
                        MUTED
                );

        PhoneEditorRow editorRow =
                new PhoneEditorRow(
                        dataId,
                        field,
                        type
                );

        remove.setOnClickListener(
                v -> {
                    phoneRows.remove(
                            editorRow
                    );
                    phonesContainer
                            .removeView(row);
                }
        );

        row.addView(
                field,
                new LinearLayout.LayoutParams(
                        0,
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        1f
                )
        );

        row.addView(
                space(dp(8))
        );
        row.addView(remove);

        phonesContainer.addView(
                row,
                margins(
                        0,
                        dp(5),
                        0,
                        dp(5)
                )
        );

        phoneRows.add(editorRow);
    }

    private void confirmDeleteGroup(
            JarvisContactStore.GroupInfo group
    ) {
        if (group == null
                || group.id <= 0L) {
            return;
        }

        new AlertDialog.Builder(this)
                .setTitle(
                        "Delete group?"
                )
                .setMessage(
                        "Delete \"" + group.title
                                + "\"? Contacts themselves will not be deleted, but group membership may also be removed from the synced account."
                )
                .setNegativeButton(
                        "Cancel",
                        null
                )
                .setPositiveButton(
                        "Delete",
                        (dialog, which) -> {
                            boolean deleted =
                                    JarvisContactStore
                                            .deleteGroup(
                                                    this,
                                                    group.id
                                            );

                            if (!deleted) {
                                Toast.makeText(
                                        this,
                                        "Unable to delete this group.",
                                        Toast.LENGTH_LONG
                                ).show();
                                return;
                            }

                            for (int i =
                                    groups.size() - 1;
                                    i >= 0;
                                    i--) {
                                if (groups.get(i).id
                                        == group.id) {
                                    groups.remove(i);
                                }
                            }

                            rebuildGroups();

                            Toast.makeText(
                                    this,
                                    "Group deleted",
                                    Toast.LENGTH_SHORT
                            ).show();
                        }
                )
                .show();
    }

    private void createGroupDialog() {
        EditText input =
                new EditText(this);

        input.setHint("Group name");
        input.setSingleLine(true);
        input.setTextColor(TEXT);
        input.setHintTextColor(MUTED);
        input.setPadding(
                dp(14),
                dp(12),
                dp(14),
                dp(12)
        );

        input.setBackground(
                rounded(
                        CARD,
                        dp(16)
                )
        );

        int pad = dp(18);

        FrameLayout wrapper =
                new FrameLayout(this);

        wrapper.setPadding(
                pad,
                dp(8),
                pad,
                0
        );

        wrapper.addView(
                input,
                new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                )
        );

        new AlertDialog.Builder(this)
                .setTitle("New group")
                .setView(wrapper)
                .setNegativeButton(
                        "Cancel",
                        null
                )
                .setPositiveButton(
                        "Create",
                        (dialog, which) -> {
                            String title =
                                    input.getText()
                                            .toString()
                                            .trim();

                            JarvisContactStore.GroupInfo created =
                                    JarvisContactStore
                                            .createGroup(
                                                    this,
                                                    title,
                                                    currentAccount()
                                            );

                            if (created == null) {
                                Toast.makeText(
                                        this,
                                        "Unable to create group for this account.",
                                        Toast.LENGTH_LONG
                                ).show();
                                return;
                            }

                            groups.add(created);
                            rebuildGroups();

                            for (
                                    GroupCheckRow row
                                    : groupRows
                            ) {
                                if (row.group.id
                                        == created.id) {
                                    row.check.setChecked(true);
                                    break;
                                }
                            }
                        }
                )
                .show();
    }

    private void pickPhoto() {
        Intent intent =
                new Intent(
                        Intent.ACTION_OPEN_DOCUMENT
                );

        intent.addCategory(
                Intent.CATEGORY_OPENABLE
        );

        intent.setType("image/*");

        startActivityForResult(
                intent,
                REQUEST_PICK_PHOTO
        );
    }

    @Override
    protected void onActivityResult(
            int requestCode,
            int resultCode,
            Intent data
    ) {
        super.onActivityResult(
                requestCode,
                resultCode,
                data
        );

        if (requestCode != REQUEST_PICK_PHOTO
                || resultCode != RESULT_OK
                || data == null
                || data.getData() == null) {
            return;
        }

        Uri uri =
                data.getData();

        try (
                InputStream input =
                        getContentResolver()
                                .openInputStream(uri)
        ) {
            Bitmap bitmap =
                    BitmapFactory.decodeStream(
                            input
                    );

            if (bitmap == null) {
                throw new IllegalStateException(
                        "Invalid image"
                );
            }

            Bitmap scaled =
                    scalePhoto(bitmap);

            ByteArrayOutputStream output =
                    new ByteArrayOutputStream();

            scaled.compress(
                    Bitmap.CompressFormat.JPEG,
                    88,
                    output
            );

            newPhotoBytes =
                    output.toByteArray();

            removePhoto = false;
            showPhoto(scaled);

        } catch (Exception ex) {
            Toast.makeText(
                    this,
                    "Unable to load photo.",
                    Toast.LENGTH_LONG
            ).show();
        }
    }

    private Bitmap scalePhoto(
            Bitmap bitmap
    ) {
        int max = 512;
        int width = bitmap.getWidth();
        int height = bitmap.getHeight();

        if (width <= max
                && height <= max) {
            return bitmap;
        }

        float ratio =
                Math.min(
                        max / (float) width,
                        max / (float) height
                );

        return Bitmap.createScaledBitmap(
                bitmap,
                Math.max(
                        1,
                        Math.round(width * ratio)
                ),
                Math.max(
                        1,
                        Math.round(height * ratio)
                ),
                true
        );
    }

    private void saveContact() {
        if (!JarvisContactStore.canWrite(
                this
        )) {
            requestPermissions(
                    new String[]{
                            Manifest.permission.WRITE_CONTACTS
                    },
                    REQUEST_WRITE_CONTACTS
            );
            return;
        }

        String name =
                nameField.getText()
                        .toString()
                        .trim();

        List<JarvisContactStore.PhoneEdit>
                phoneEdits =
                new ArrayList<>();

        for (
                PhoneEditorRow row
                : phoneRows
        ) {
            phoneEdits.add(
                    new JarvisContactStore
                            .PhoneEdit(
                                    row.dataId,
                                    row.field
                                            .getText()
                                            .toString(),
                                    row.type,
                                    ""
                            )
            );
        }

        Set<Long> selectedGroups =
                new LinkedHashSet<>();

        for (
                GroupCheckRow row
                : groupRows
        ) {
            if (row.check.isChecked()) {
                selectedGroups.add(
                        row.group.id
                );
            }
        }

        JarvisContactStore.SaveResult result;

        if (original == null) {
            result =
                    JarvisContactStore
                            .createContact(
                                    this,
                                    name,
                                    phoneEdits,
                                    favoriteCheck
                                            .isChecked(),
                                    currentAccount(),
                                    selectedGroups,
                                    newPhotoBytes
                            );
        } else {
            result =
                    JarvisContactStore
                            .updateContact(
                                    this,
                                    original,
                                    name,
                                    phoneEdits,
                                    favoriteCheck
                                            .isChecked(),
                                    selectedGroups,
                                    newPhotoBytes,
                                    removePhoto
                            );
        }

        if (!result.ok) {
            Toast.makeText(
                    this,
                    result.message,
                    Toast.LENGTH_LONG
            ).show();
            return;
        }

        Toast.makeText(
                this,
                "Contact saved",
                Toast.LENGTH_SHORT
        ).show();

        setResult(RESULT_OK);
        finish();
    }

    private void confirmDelete() {
        new AlertDialog.Builder(this)
                .setTitle("Delete contact?")
                .setMessage(
                        "This removes the contact from the Android contact store and its synced account where supported."
                )
                .setNegativeButton(
                        "Cancel",
                        null
                )
                .setPositiveButton(
                        "Delete",
                        (dialog, which) -> {
                            boolean deleted =
                                    JarvisContactStore
                                            .deleteContact(
                                                    this,
                                                    contactId
                                            );

                            if (!deleted) {
                                Toast.makeText(
                                        this,
                                        "Unable to delete contact.",
                                        Toast.LENGTH_LONG
                                ).show();
                                return;
                            }

                            setResult(
                                    RESULT_OK
                            );

                            finish();
                        }
                )
                .show();
    }

    private JarvisContactStore.AccountInfo
    currentAccount() {
        if (original != null) {
            return original.account;
        }

        if (accounts.isEmpty()) {
            return new JarvisContactStore
                    .AccountInfo(
                            "",
                            ""
                    );
        }

        int position =
                accountSpinner == null
                        ? 0
                        : accountSpinner
                        .getSelectedItemPosition();

        if (position < 0
                || position >= accounts.size()) {
            position = 0;
        }

        return accounts.get(position);
    }

    private void showPhoto(
            Bitmap bitmap
    ) {
        if (bitmap == null) {
            photoView.setImageDrawable(null);
            photoView.setVisibility(
                    View.GONE
            );
            initialView.setVisibility(
                    View.VISIBLE
            );
        } else {
            photoView.setImageBitmap(bitmap);
            photoView.setVisibility(
                    View.VISIBLE
            );
            initialView.setVisibility(
                    View.GONE
            );
        }

        updateInitial();
    }

    private void updateInitial() {
        if (initialView == null
                || nameField == null) {
            return;
        }

        String name =
                nameField.getText()
                        .toString()
                        .trim();

        initialView.setText(
                name.isEmpty()
                        ? "?"
                        : name.substring(0, 1)
                        .toUpperCase()
        );
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

        if (requestCode
                != REQUEST_WRITE_CONTACTS) {
            return;
        }

        boolean granted = true;

        for (int result : grantResults) {
            if (result
                    != PackageManager
                    .PERMISSION_GRANTED) {
                granted = false;
                break;
            }
        }

        if (!granted) {
            Toast.makeText(
                    this,
                    "Contacts permission is required for the JARVIS contact editor.",
                    Toast.LENGTH_LONG
            ).show();
        }
    }

    private EditText input(
            String hint
    ) {
        EditText field =
                new EditText(this);

        field.setHint(hint);
        field.setHintTextColor(MUTED);
        field.setTextColor(TEXT);
        field.setTextSize(16f);
        field.setSingleLine(true);
        field.setPadding(
                dp(14),
                dp(12),
                dp(14),
                dp(12)
        );
        field.setBackground(
                rounded(
                        CARD,
                        dp(16)
                )
        );

        return field;
    }

    private void styleAccountRow(
            TextView view,
            boolean dropdown
    ) {
        if (view == null) {
            return;
        }

        view.setTextColor(TEXT);
        view.setTextSize(15f);
        view.setPadding(
                dp(14),
                dp(12),
                dp(14),
                dp(12)
        );

        view.setBackground(
                rounded(
                        dropdown
                                ? CARD_2
                                : CARD,
                        dp(12)
                )
        );
    }

    private TextView sectionLabel(
            String value
    ) {
        TextView label =
                new TextView(this);

        label.setText(value);
        label.setTextColor(TEXT);
        label.setTextSize(14f);
        label.setTypeface(
                Typeface.DEFAULT_BOLD
        );

        return label;
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

    private TextView chip(
            String label,
            int background,
            int foreground
    ) {
        TextView chip =
                new TextView(this);

        chip.setText(label);
        chip.setTextColor(foreground);
        chip.setTextSize(12f);
        chip.setTypeface(
                Typeface.DEFAULT_BOLD
        );
        chip.setGravity(Gravity.CENTER);
        chip.setPadding(
                dp(14),
                dp(10),
                dp(14),
                dp(10)
        );
        chip.setBackground(
                rounded(
                        background,
                        dp(18)
                )
        );

        return chip;
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

    private LinearLayout.LayoutParams margins(
            int left,
            int top,
            int right,
            int bottom
    ) {
        LinearLayout.LayoutParams params =
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                );

        params.setMargins(
                left,
                top,
                right,
                bottom
        );

        return params;
    }

    private View space(
            int width
    ) {
        android.widget.Space space =
                new android.widget.Space(this);

        space.setLayoutParams(
                new LinearLayout.LayoutParams(
                        width,
                        1
                )
        );

        return space;
    }

    private int dp(
            int value
    ) {
        return Math.round(
                value
                        * getResources()
                        .getDisplayMetrics()
                        .density
        );
    }

    private static final class PhoneEditorRow {
        final long dataId;
        final EditText field;
        final int type;

        PhoneEditorRow(
                long dataId,
                EditText field,
                int type
        ) {
            this.dataId = dataId;
            this.field = field;
            this.type = type;
        }
    }

    private static final class GroupCheckRow {
        final JarvisContactStore.GroupInfo group;
        final CheckBox check;

        GroupCheckRow(
                JarvisContactStore.GroupInfo group,
                CheckBox check
        ) {
            this.group = group;
            this.check = check;
        }
    }
}
