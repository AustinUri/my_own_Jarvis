package com.jarvis.companion;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.telecom.Call;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.GridLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.Space;
import android.widget.TextView;

import java.util.List;
import java.util.Locale;

public final class JarvisCallActivity
        extends Activity {

    private static final int BG =
            Color.rgb(5, 10, 18);

    private static final int CARD =
            Color.rgb(15, 23, 34);

    private static final int CARD_ACTIVE =
            Color.rgb(54, 40, 24);

    private static final int TEXT =
            Color.rgb(245, 247, 250);

    private static final int MUTED =
            Color.rgb(148, 163, 184);

    private static final int ORANGE =
            Color.rgb(255, 153, 61);

    private static final int GREEN =
            Color.rgb(46, 204, 113);

    private static final int RED =
            Color.rgb(239, 68, 68);

    private TextView stateView;
    private TextView nameView;
    private TextView numberView;
    private TextView sourceView;
    private ImageView photoView;
    private TextView initialsView;

    private LinearLayout ringingRow;
    private LinearLayout callStackPanel;
    private TextView operationView;
    private GridLayout controlsGrid;
    private LinearLayout dtmfPanel;
    private LinearLayout hangupRow;

    private boolean keypadVisible = false;

    private final Handler timerHandler =
            new Handler(
                    Looper.getMainLooper()
            );

    private final Runnable timerTick =
            new Runnable() {
                @Override
                public void run() {
                    updateStateLine();
                    timerHandler.postDelayed(
                            this,
                            1000L
                    );
                }
            };

    private final BroadcastReceiver uiReceiver =
            new BroadcastReceiver() {

        @Override
        public void onReceive(
                Context context,
                Intent intent
        ) {
            refresh();
        }
    };

    @Override
    protected void onCreate(
            Bundle savedInstanceState
    ) {
        super.onCreate(savedInstanceState);

        setShowWhenLocked(true);
        setTurnScreenOn(true);

        Window window =
                getWindow();

        window.setStatusBarColor(BG);
        window.setNavigationBarColor(BG);

        window.addFlags(
                WindowManager.LayoutParams
                        .FLAG_KEEP_SCREEN_ON
        );

        setContentView(buildUi());

        registerUiReceiver();
        handleAction(getIntent());
        refresh();
    }

    @Override
    protected void onNewIntent(
            Intent intent
    ) {
        super.onNewIntent(intent);

        setIntent(intent);
        handleAction(intent);
        refresh();
    }

    @Override
    protected void onResume() {
        super.onResume();

        timerHandler.removeCallbacks(
                timerTick
        );
        timerHandler.post(timerTick);

        refresh();
    }

    @Override
    protected void onPause() {
        timerHandler.removeCallbacks(
                timerTick
        );

        super.onPause();
    }

    @Override
    protected void onDestroy() {
        timerHandler.removeCallbacks(
                timerTick
        );

        try {
            unregisterReceiver(uiReceiver);
        } catch (Exception ignored) {
        }

        JarvisInCallService.stopDtmf();

        super.onDestroy();
    }

    private void handleAction(
            Intent intent
    ) {
        if (intent == null
                || intent.getAction() == null) {
            return;
        }

        switch (intent.getAction()) {
            case JarvisInCallService.ACTION_ANSWER:
                JarvisInCallService
                        .answerCurrentCall();
                break;

            case JarvisInCallService.ACTION_REJECT:
                JarvisInCallService
                        .rejectCurrentCall();
                break;

            case JarvisInCallService.ACTION_HANGUP:
                JarvisInCallService
                        .hangupCurrentCall();
                break;

            default:
                break;
        }
    }

    private View buildUi() {
        LinearLayout root =
                new LinearLayout(this);

        root.setOrientation(
                LinearLayout.VERTICAL
        );

        root.setGravity(
                Gravity.CENTER_HORIZONTAL
        );

        root.setPadding(
                dp(24),
                dp(28),
                dp(24),
                dp(24)
        );

        root.setBackgroundColor(BG);

        TextView brand =
                new TextView(this);

        brand.setText("J A R V I S");
        brand.setTextColor(ORANGE);
        brand.setTextSize(13f);
        brand.setTypeface(
                Typeface.DEFAULT_BOLD
        );
        brand.setLetterSpacing(0.14f);
        brand.setGravity(Gravity.CENTER);

        root.addView(
                brand,
                fullWidthWrap()
        );

        stateView =
                new TextView(this);

        stateView.setTextColor(MUTED);
        stateView.setTextSize(14f);
        stateView.setGravity(Gravity.CENTER);

        LinearLayout.LayoutParams stateParams =
                fullWidthWrap();

        stateParams.topMargin =
                dp(10);

        root.addView(
                stateView,
                stateParams
        );

        FrameLayout avatar =
                new FrameLayout(this);

        avatar.setBackground(
                circle(
                        CARD,
                        ORANGE,
                        dp(2)
                )
        );

        LinearLayout.LayoutParams avatarParams =
                new LinearLayout.LayoutParams(
                        dp(132),
                        dp(132)
                );

        avatarParams.gravity =
                Gravity.CENTER_HORIZONTAL;

        avatarParams.topMargin =
                dp(22);

        root.addView(
                avatar,
                avatarParams
        );

        photoView =
                new ImageView(this);

        photoView.setScaleType(
                ImageView.ScaleType.CENTER_CROP
        );

        photoView.setClipToOutline(true);

        avatar.addView(
                photoView,
                matchParent()
        );

        initialsView =
                new TextView(this);

        initialsView.setTextColor(TEXT);
        initialsView.setTextSize(46f);
        initialsView.setTypeface(
                Typeface.DEFAULT_BOLD
        );
        initialsView.setGravity(
                Gravity.CENTER
        );

        avatar.addView(
                initialsView,
                matchParent()
        );

        nameView =
                new TextView(this);

        nameView.setTextColor(TEXT);
        nameView.setTextSize(28f);
        nameView.setTypeface(
                Typeface.DEFAULT_BOLD
        );
        nameView.setGravity(Gravity.CENTER);
        nameView.setMaxLines(2);

        LinearLayout.LayoutParams nameParams =
                fullWidthWrap();

        nameParams.topMargin =
                dp(18);

        root.addView(
                nameView,
                nameParams
        );

        numberView =
                new TextView(this);

        numberView.setTextColor(MUTED);
        numberView.setTextSize(16f);
        numberView.setGravity(Gravity.CENTER);

        LinearLayout.LayoutParams numberParams =
                fullWidthWrap();

        numberParams.topMargin =
                dp(5);

        root.addView(
                numberView,
                numberParams
        );

        sourceView =
                new TextView(this);

        sourceView.setTextColor(
                Color.rgb(100, 116, 139)
        );

        sourceView.setTextSize(11f);
        sourceView.setGravity(Gravity.CENTER);

        LinearLayout.LayoutParams sourceParams =
                fullWidthWrap();

        sourceParams.topMargin =
                dp(5);

        root.addView(
                sourceView,
                sourceParams
        );

        operationView =
                new TextView(this);

        operationView.setTextColor(ORANGE);
        operationView.setTextSize(12f);
        operationView.setGravity(Gravity.CENTER);
        operationView.setVisibility(View.GONE);

        LinearLayout.LayoutParams operationParams =
                fullWidthWrap();

        operationParams.topMargin = dp(8);

        root.addView(
                operationView,
                operationParams
        );

        callStackPanel =
                new LinearLayout(this);

        callStackPanel.setOrientation(
                LinearLayout.VERTICAL
        );

        callStackPanel.setVisibility(
                View.GONE
        );

        LinearLayout.LayoutParams stackParams =
                fullWidthWrap();

        stackParams.topMargin = dp(12);

        root.addView(
                callStackPanel,
                stackParams
        );

        Space spacer =
                new Space(this);

        root.addView(
                spacer,
                new LinearLayout.LayoutParams(
                        1,
                        dp(12)
                )
        );

        ringingRow =
                new LinearLayout(this);

        ringingRow.setOrientation(
                LinearLayout.HORIZONTAL
        );

        ringingRow.setGravity(
                Gravity.CENTER
        );

        root.addView(
                ringingRow,
                fullWidthWrap()
        );

        controlsGrid =
                new GridLayout(this);

        controlsGrid.setColumnCount(3);
        controlsGrid.setAlignmentMode(
                GridLayout.ALIGN_BOUNDS
        );

        root.addView(
                controlsGrid,
                fullWidthWrap()
        );

        dtmfPanel =
                buildDtmfPanel();

        dtmfPanel.setVisibility(
                View.GONE
        );

        root.addView(
                dtmfPanel,
                fullWidthWrap()
        );

        hangupRow =
                new LinearLayout(this);

        hangupRow.setOrientation(
                LinearLayout.HORIZONTAL
        );

        hangupRow.setGravity(
                Gravity.CENTER
        );

        LinearLayout.LayoutParams hangParams =
                fullWidthWrap();

        hangParams.topMargin =
                dp(14);

        root.addView(
                hangupRow,
                hangParams
        );

        return root;
    }

    private void refresh() {
        if (!JarvisInCallService
                .hasCurrentCall()) {
            finish();
            return;
        }

        String name =
                JarvisInCallService
                        .currentDisplayName();

        String number =
                JarvisInCallService
                        .currentNumber();

        Bitmap photo =
                JarvisInCallService
                        .currentPhoto();

        nameView.setText(
                safeName(name)
        );

        numberView.setText(
                number == null
                        || number.trim().isEmpty()
                        ? ""
                        : number
        );

        String source =
                JarvisInCallService
                        .currentIdentitySource();

        if ("jarvis_oracle".equals(source)) {
            sourceView.setText(
                    "Known by JARVIS"
            );
        } else if ("contacts".equals(source)) {
            sourceView.setText(
                    "Contacts"
            );
        } else if ("conference".equals(source)) {
            sourceView.setText(
                    "Multi-party call"
            );
        } else {
            sourceView.setText("");
        }

        if (photo != null) {
            photoView.setImageBitmap(photo);
            photoView.setVisibility(
                    View.VISIBLE
            );
            initialsView.setVisibility(
                    View.GONE
            );
        } else {
            photoView.setImageDrawable(null);
            photoView.setVisibility(
                    View.GONE
            );
            initialsView.setVisibility(
                    View.VISIBLE
            );
            initialsView.setText(
                    initialFor(name)
            );
        }

        updateStateLine();
        renderCallStack();
        renderOperationMessage();
        rebuildActions();
    }

    private void updateStateLine() {
        String state =
                JarvisInCallService
                        .currentStateLabel();

        int callState =
                JarvisInCallService
                        .currentState();

        long connectedAt =
                JarvisInCallService
                        .currentConnectTimeMillis();

        if ((callState == Call.STATE_ACTIVE
                || callState
                == Call.STATE_HOLDING)
                && connectedAt > 0L) {

            long elapsed =
                    Math.max(
                            0L,
                            System.currentTimeMillis()
                                    - connectedAt
                    ) / 1000L;

            state =
                    state
                            + "  \u2022  "
                            + formatDuration(
                            elapsed
                    );
        }

        stateView.setText(
                state.toUpperCase(
                        Locale.getDefault()
                )
        );
    }

    private String formatDuration(
            long seconds
    ) {
        long hours =
                seconds / 3600L;

        long minutes =
                (seconds % 3600L) / 60L;

        long secs =
                seconds % 60L;

        if (hours > 0L) {
            return String.format(
                    Locale.US,
                    "%d:%02d:%02d",
                    hours,
                    minutes,
                    secs
            );
        }

        return String.format(
                Locale.US,
                "%02d:%02d",
                minutes,
                secs
        );
    }

    private void rebuildActions() {
        ringingRow.removeAllViews();
        controlsGrid.removeAllViews();
        hangupRow.removeAllViews();

        int state =
                JarvisInCallService
                        .currentState();

        boolean ringing =
                state == Call.STATE_RINGING
                        || state
                        == Call.STATE_SIMULATED_RINGING;

        ringingRow.setVisibility(
                ringing
                        ? View.VISIBLE
                        : View.GONE
        );

        controlsGrid.setVisibility(
                ringing
                        ? View.GONE
                        : View.VISIBLE
        );

        hangupRow.setVisibility(
                ringing
                        ? View.GONE
                        : View.VISIBLE
        );

        if (ringing) {
            keypadVisible = false;
            dtmfPanel.setVisibility(
                    View.GONE
            );

            ringingRow.addView(
                    callButton(
                            "\u2715",
                            "Reject",
                            RED,
                            v -> {
                                JarvisInCallService
                                        .rejectCurrentCall();
                            }
                    )
            );

            ringingRow.addView(
                    gap(dp(54))
            );

            ringingRow.addView(
                    callButton(
                            "\u260e",
                            "Answer",
                            GREEN,
                            v -> {
                                JarvisInCallService
                                        .answerCurrentCall();
                            }
                    )
            );

            return;
        }

        boolean active =
                state == Call.STATE_ACTIVE;

        boolean holding =
                state == Call.STATE_HOLDING;

        if (!active && !holding
                && state != Call.STATE_DIALING
                && state != Call.STATE_CONNECTING) {
            return;
        }

        addControl(
                "M",
                JarvisInCallService
                        .isMuted()
                        ? "Unmute"
                        : "Mute",
                JarvisInCallService
                        .isMuted(),
                v -> {
                    JarvisInCallService
                            .toggleMute();
                    refresh();
                }
        );

        if (active) {
            addControl(
                    "#",
                    "Keypad",
                    keypadVisible,
                    v -> {
                        keypadVisible =
                                !keypadVisible;

                        dtmfPanel.setVisibility(
                                keypadVisible
                                        ? View.VISIBLE
                                        : View.GONE
                        );

                        rebuildActions();
                    }
            );
        }

        addControl(
                "S",
                "Speaker",
                JarvisInCallService
                        .isSpeakerOn(),
                v -> {
                    JarvisInCallService
                            .toggleSpeaker();
                    refresh();
                }
        );

        if (JarvisInCallService
                .canHoldCurrentCall()) {

            addControl(
                    holding
                            ? "\u25b6"
                            : "\u2161",
                    holding
                            ? "Resume"
                            : "Hold",
                    holding,
                    v -> {
                        JarvisInCallService
                                .toggleHoldCurrentCall();
                        refresh();
                    }
            );
        }

        if (JarvisInCallService
                .canAddCallNow()) {

            addControl(
                    "+",
                    "Add call",
                    false,
                    v -> {
                        Intent intent =
                                new Intent(
                                        this,
                                        JarvisDialerActivity.class
                                );

                        intent.putExtra(
                                JarvisDialerActivity
                                        .EXTRA_ADD_CALL_MODE,
                                true
                        );

                        startActivity(intent);
                    }
            );
        }

        if (JarvisInCallService
                .canSwapCalls()) {

            addControl(
                    "\u21c4",
                    "Switch",
                    false,
                    v -> {
                        JarvisInCallService
                                .swapCalls();
                        refresh();
                    }
            );
        }

        if (JarvisInCallService
                .canMergeCalls()) {

            addControl(
                    "\u22c8",
                    "Merge",
                    false,
                    v -> {
                        JarvisInCallService
                                .mergeCalls();
                        refresh();
                    }
            );
        }

        hangupRow.addView(
                callButton(
                        "\u260e",
                        "Hang up",
                        RED,
                        v -> {
                            JarvisInCallService
                                    .hangupCurrentCall();
                        }
                )
        );
    }

    private void renderOperationMessage() {
        String message =
                JarvisInCallService
                        .lastOperationMessage();

        if (message == null
                || message.trim().isEmpty()) {
            operationView.setText("");
            operationView.setVisibility(
                    View.GONE
            );
            return;
        }

        operationView.setText(message);
        operationView.setVisibility(
                View.VISIBLE
        );
    }

    private void renderCallStack() {
        callStackPanel.removeAllViews();

        List<JarvisInCallService.CallSnapshot> snapshots =
                JarvisInCallService
                        .visibleCallSnapshots();

        boolean conference =
                "conference".equals(
                        JarvisInCallService
                                .currentIdentitySource()
                );

        if (snapshots == null
                || snapshots.isEmpty()
                || (
                snapshots.size() == 1
                        && !conference
        )) {
            callStackPanel.setVisibility(
                    View.GONE
            );
            return;
        }

        callStackPanel.setVisibility(
                View.VISIBLE
        );

        TextView title =
                new TextView(this);

        title.setText(
                conference
                        ? "CONFERENCE PARTICIPANTS"
                        : "CALLS"
        );
        title.setTextColor(MUTED);
        title.setTextSize(11f);
        title.setTypeface(
                Typeface.DEFAULT_BOLD
        );
        title.setLetterSpacing(0.08f);

        callStackPanel.addView(
                title,
                fullWidthWrap()
        );

        for (JarvisInCallService.CallSnapshot snapshot
                : snapshots) {

            callStackPanel.addView(
                    callSnapshotCard(snapshot),
                    stackCardParams()
            );
        }
    }

    private View callSnapshotCard(
            JarvisInCallService.CallSnapshot snapshot
    ) {
        LinearLayout row =
                new LinearLayout(this);

        row.setOrientation(
                LinearLayout.HORIZONTAL
        );
        row.setGravity(
                Gravity.CENTER_VERTICAL
        );
        row.setPadding(
                dp(12),
                dp(9),
                dp(12),
                dp(9)
        );

        boolean held =
                "ON HOLD".equals(
                        snapshot.role
                );

        boolean active =
                "ACTIVE".equals(
                        snapshot.role
                );

        row.setBackground(
                roundedRect(
                        active
                                ? Color.rgb(24, 35, 48)
                                : CARD,
                        dp(14),
                        active
                                ? ORANGE
                                : Color.rgb(45, 58, 75),
                        dp(1)
                )
        );

        TextView status =
                new TextView(this);

        status.setText(snapshot.role);
        status.setTextColor(
                held
                        ? MUTED
                        : ORANGE
        );
        status.setTextSize(10f);
        status.setTypeface(
                Typeface.DEFAULT_BOLD
        );
        status.setGravity(
                Gravity.CENTER
        );
        status.setPadding(
                dp(7),
                dp(5),
                dp(7),
                dp(5)
        );

        LinearLayout text =
                new LinearLayout(this);

        text.setOrientation(
                LinearLayout.VERTICAL
        );
        text.setPadding(
                dp(10),
                0,
                0,
                0
        );

        TextView name =
                new TextView(this);

        name.setText(
                safeName(
                        snapshot.displayName
                )
        );
        name.setTextColor(TEXT);
        name.setTextSize(15f);
        name.setTypeface(
                Typeface.DEFAULT_BOLD
        );

        TextView number =
                new TextView(this);

        number.setText(
                snapshot.number == null
                        ? ""
                        : snapshot.number
        );
        number.setTextColor(MUTED);
        number.setTextSize(12f);

        text.addView(name);

        if (snapshot.number != null
                && !snapshot.number
                .trim()
                .isEmpty()) {
            text.addView(number);
        }

        row.addView(status);
        row.addView(
                text,
                new LinearLayout.LayoutParams(
                        0,
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        1f
                )
        );

        return row;
    }

    private LinearLayout.LayoutParams stackCardParams() {
        LinearLayout.LayoutParams params =
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                );

        params.topMargin = dp(6);
        return params;
    }

    private GradientDrawable roundedRect(
            int fill,
            int radius,
            int stroke,
            int strokeWidth
    ) {
        GradientDrawable drawable =
                new GradientDrawable();

        drawable.setColor(fill);
        drawable.setCornerRadius(radius);

        if (strokeWidth > 0) {
            drawable.setStroke(
                    strokeWidth,
                    stroke
            );
        }

        return drawable;
    }

    private void addControl(
            String symbol,
            String label,
            boolean selected,
            View.OnClickListener listener
    ) {
        View button =
                controlButton(
                        symbol,
                        label,
                        selected,
                        listener
                );

        GridLayout.LayoutParams lp =
                new GridLayout.LayoutParams();

        lp.width = 0;
        lp.height =
                ViewGroup.LayoutParams.WRAP_CONTENT;

        lp.columnSpec =
                GridLayout.spec(
                        GridLayout.UNDEFINED,
                        1f
                );

        lp.setMargins(
                dp(7),
                dp(8),
                dp(7),
                dp(8)
        );

        controlsGrid.addView(
                button,
                lp
        );
    }

    private View controlButton(
            String symbol,
            String label,
            boolean selected,
            View.OnClickListener listener
    ) {
        LinearLayout wrapper =
                new LinearLayout(this);

        wrapper.setOrientation(
                LinearLayout.VERTICAL
        );

        wrapper.setGravity(
                Gravity.CENTER
        );

        TextView circleView =
                new TextView(this);

        circleView.setText(symbol);
        circleView.setTextColor(
                selected
                        ? ORANGE
                        : TEXT
        );

        circleView.setTextSize(22f);
        circleView.setGravity(
                Gravity.CENTER
        );
        circleView.setTypeface(
                Typeface.DEFAULT_BOLD
        );

        circleView.setBackground(
                circle(
                        selected
                                ? CARD_ACTIVE
                                : CARD,
                        selected
                                ? ORANGE
                                : Color.rgb(
                                48,
                                61,
                                79
                        ),
                        dp(1)
                )
        );

        circleView.setOnClickListener(
                listener
        );

        wrapper.addView(
                circleView,
                new LinearLayout.LayoutParams(
                        dp(64),
                        dp(64)
                )
        );

        TextView caption =
                new TextView(this);

        caption.setText(label);
        caption.setTextColor(
                selected
                        ? ORANGE
                        : TEXT
        );
        caption.setTextSize(12f);
        caption.setGravity(
                Gravity.CENTER
        );

        LinearLayout.LayoutParams captionParams =
                fullWidthWrap();

        captionParams.topMargin =
                dp(6);

        wrapper.addView(
                caption,
                captionParams
        );

        return wrapper;
    }

    private LinearLayout buildDtmfPanel() {
        LinearLayout panel =
                new LinearLayout(this);

        panel.setOrientation(
                LinearLayout.VERTICAL
        );

        panel.setPadding(
                dp(8),
                dp(8),
                dp(8),
                dp(6)
        );

        TextView title =
                new TextView(this);

        title.setText(
                "DTMF KEYPAD"
        );
        title.setTextColor(MUTED);
        title.setTextSize(11f);
        title.setGravity(Gravity.CENTER);

        panel.addView(
                title,
                fullWidthWrap()
        );

        GridLayout grid =
                new GridLayout(this);

        grid.setColumnCount(3);

        String[] keys =
                new String[]{
                        "1", "2", "3",
                        "4", "5", "6",
                        "7", "8", "9",
                        "*", "0", "#"
                };

        for (String key : keys) {
            TextView button =
                    new TextView(this);

            button.setText(key);
            button.setTag(key);
            button.setTextColor(TEXT);
            button.setTextSize(24f);
            button.setGravity(
                    Gravity.CENTER
            );
            button.setBackground(
                    circle(
                            CARD,
                            Color.rgb(
                                    48,
                                    61,
                                    79
                            ),
                            dp(1)
                    )
            );

            button.setOnTouchListener(
                    (view, event) -> {
                        String value =
                                String.valueOf(
                                        view.getTag()
                                );

                        if (value.isEmpty()) {
                            return false;
                        }

                        char digit =
                                value.charAt(0);

                        if (event.getAction()
                                == MotionEvent.ACTION_DOWN) {

                            JarvisInCallService
                                    .playDtmf(
                                            digit
                                    );

                            return true;
                        }

                        if (event.getAction()
                                == MotionEvent.ACTION_UP
                                || event.getAction()
                                == MotionEvent.ACTION_CANCEL) {

                            JarvisInCallService
                                    .stopDtmf();

                            view.performClick();
                            return true;
                        }

                        return true;
                    }
            );

            GridLayout.LayoutParams lp =
                    new GridLayout.LayoutParams();

            lp.width = 0;
            lp.height = dp(58);

            lp.columnSpec =
                    GridLayout.spec(
                            GridLayout.UNDEFINED,
                            1f
                    );

            lp.setMargins(
                    dp(6),
                    dp(6),
                    dp(6),
                    dp(6)
            );

            grid.addView(
                    button,
                    lp
            );
        }

        panel.addView(
                grid,
                fullWidthWrap()
        );

        return panel;
    }

    private View callButton(
            String symbol,
            String label,
            int color,
            View.OnClickListener listener
    ) {
        LinearLayout wrapper =
                new LinearLayout(this);

        wrapper.setOrientation(
                LinearLayout.VERTICAL
        );

        wrapper.setGravity(
                Gravity.CENTER
        );

        TextView circleView =
                new TextView(this);

        circleView.setText(symbol);
        circleView.setTextColor(
                Color.WHITE
        );
        circleView.setTextSize(28f);
        circleView.setGravity(
                Gravity.CENTER
        );
        circleView.setTypeface(
                Typeface.DEFAULT_BOLD
        );

        circleView.setBackground(
                circle(
                        color,
                        Color.TRANSPARENT,
                        0
                )
        );

        circleView.setElevation(dp(6));
        circleView.setOnClickListener(
                listener
        );

        wrapper.addView(
                circleView,
                new LinearLayout.LayoutParams(
                        dp(74),
                        dp(74)
                )
        );

        TextView caption =
                new TextView(this);

        caption.setText(label);
        caption.setTextColor(TEXT);
        caption.setTextSize(13f);
        caption.setGravity(Gravity.CENTER);

        LinearLayout.LayoutParams captionParams =
                fullWidthWrap();

        captionParams.topMargin =
                dp(7);

        wrapper.addView(
                caption,
                captionParams
        );

        return wrapper;
    }

    private View gap(
            int width
    ) {
        Space gap =
                new Space(this);

        gap.setLayoutParams(
                new LinearLayout.LayoutParams(
                        width,
                        1
                )
        );

        return gap;
    }

    private String safeName(
            String name
    ) {
        if (name == null
                || name.trim().isEmpty()) {
            return "Unknown caller";
        }

        return name.trim();
    }

    private String initialFor(
            String name
    ) {
        String clean =
                safeName(name);

        if ("Unknown caller".equals(clean)
                || "Conference call".equals(clean)
                || "Conference".equals(clean)) {
            return clean.startsWith("Conference")
                    ? "C"
                    : "?";
        }

        return clean.substring(0, 1)
                .toUpperCase();
    }

    private GradientDrawable circle(
            int fill,
            int stroke,
            int strokeWidth
    ) {
        GradientDrawable drawable =
                new GradientDrawable();

        drawable.setShape(
                GradientDrawable.OVAL
        );

        drawable.setColor(fill);

        if (strokeWidth > 0) {
            drawable.setStroke(
                    strokeWidth,
                    stroke
            );
        }

        return drawable;
    }

    private FrameLayout.LayoutParams matchParent() {
        return new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        );
    }

    private LinearLayout.LayoutParams fullWidthWrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
    }

    private int dp(int value) {
        return Math.round(
                value
                        * getResources()
                        .getDisplayMetrics()
                        .density
        );
    }

    private void registerUiReceiver() {
        IntentFilter filter =
                new IntentFilter(
                        JarvisInCallService
                                .ACTION_UI_UPDATE
                );

        if (Build.VERSION.SDK_INT
                >= Build.VERSION_CODES.TIRAMISU) {

            registerReceiver(
                    uiReceiver,
                    filter,
                    Context.RECEIVER_NOT_EXPORTED
            );

        } else {

            registerReceiver(
                    uiReceiver,
                    filter
            );
        }
    }
}
