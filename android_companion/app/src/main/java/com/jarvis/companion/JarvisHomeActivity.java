package com.jarvis.companion;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

public final class JarvisHomeActivity extends Activity {

    private static final int BG = Color.rgb(4, 9, 16);
    private static final int CARD = Color.rgb(15, 23, 34);
    private static final int TEXT = Color.rgb(248, 250, 252);
    private static final int MUTED = Color.rgb(148, 163, 184);
    private static final int ORANGE = Color.rgb(255, 153, 61);

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);

        setContentView(buildUi());
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);
        root.setPadding(dp(22), dp(28), dp(22), dp(28));

        TextView brand = new TextView(this);
        brand.setText("J A R V I S");
        brand.setTextColor(ORANGE);
        brand.setTextSize(13f);
        brand.setTypeface(Typeface.DEFAULT_BOLD);
        brand.setLetterSpacing(0.14f);

        TextView title = new TextView(this);
        title.setText("Companion");
        title.setTextColor(TEXT);
        title.setTextSize(32f);
        title.setTypeface(Typeface.DEFAULT_BOLD);

        TextView status = new TextView(this);
        status.setText("Oracle cloud link is managed automatically.");
        status.setTextColor(MUTED);
        status.setTextSize(14f);

        root.addView(brand);
        root.addView(title, margins(0, dp(3), 0, 0));
        root.addView(status, margins(0, dp(6), 0, dp(24)));

        root.addView(
                card(
                        "Phone",
                        "Calls, recents, contacts and keypad",
                        v -> startActivity(
                                new Intent(
                                        this,
                                        JarvisDialerActivity.class
                                )
                        )
                ),
                margins(0, 0, 0, dp(12))
        );

        root.addView(
                card(
                        "App settings",
                        "Permissions, notifications and Android settings",
                        v -> {
                            Intent intent =
                                    new Intent(
                                            Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                                            Uri.parse(
                                                    "package:" + getPackageName()
                                            )
                                    );
                            startActivity(intent);
                        }
                ),
                margins(0, 0, 0, dp(12))
        );

        root.addView(
                card(
                        "Advanced diagnostics",
                        "Legacy connection screen — only if troubleshooting is needed",
                        v -> startActivity(
                                new Intent(
                                        this,
                                        MainActivity.class
                                )
                        )
                ),
                margins(0, 0, 0, dp(12))
        );

        TextView note = new TextView(this);
        note.setText(
                "The old pairing screen is no longer the normal entry point."
        );
        note.setTextColor(MUTED);
        note.setTextSize(12f);
        root.addView(note, margins(0, dp(8), 0, 0));

        return root;
    }

    private View card(
            String title,
            String subtitle,
            View.OnClickListener listener
    ) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(18), dp(18), dp(18), dp(18));
        card.setBackground(rounded(CARD, dp(18)));
        card.setClickable(true);
        card.setFocusable(true);
        card.setOnClickListener(listener);

        TextView heading = new TextView(this);
        heading.setText(title);
        heading.setTextColor(TEXT);
        heading.setTextSize(19f);
        heading.setTypeface(Typeface.DEFAULT_BOLD);

        TextView body = new TextView(this);
        body.setText(subtitle);
        body.setTextColor(MUTED);
        body.setTextSize(14f);

        card.addView(heading);
        card.addView(body, margins(0, dp(5), 0, 0));

        return card;
    }

    private GradientDrawable rounded(int color, int radius) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(radius);
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
        params.setMargins(left, top, right, bottom);
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
}
