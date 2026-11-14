package com.jarvis.companion;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.graphics.drawable.Icon;
import android.os.Build;

import java.util.Collections;

public final class JarvisPhoneShortcutHelper {

    private static final String SHORTCUT_ID =
            "jarvis_phone";

    private JarvisPhoneShortcutHelper() {
    }

    public static void ensureDynamicShortcut(
            Context context
    ) {
        if (context == null
                || Build.VERSION.SDK_INT
                < Build.VERSION_CODES.N_MR1) {
            return;
        }

        ShortcutManager manager =
                context.getSystemService(
                        ShortcutManager.class
                );

        if (manager == null) {
            return;
        }

        Intent intent =
                new Intent(
                        context,
                        JarvisDialerActivity.class
                );

        intent.setAction(
                Intent.ACTION_VIEW
        );

        ShortcutInfo shortcut =
                new ShortcutInfo.Builder(
                        context,
                        SHORTCUT_ID
                )
                        .setShortLabel(
                                "Phone"
                        )
                        .setLongLabel(
                                "JARVIS Phone"
                        )
                        .setIcon(
                                Icon.createWithResource(
                                        context,
                                        android.R.drawable
                                                .sym_action_call
                                )
                        )
                        .setIntent(intent)
                        .build();

        manager.setDynamicShortcuts(
                Collections.singletonList(
                        shortcut
                )
        );
    }

    public static boolean requestPinnedShortcut(
            Context context
    ) {
        if (context == null
                || Build.VERSION.SDK_INT
                < Build.VERSION_CODES.O) {
            return false;
        }

        ShortcutManager manager =
                context.getSystemService(
                        ShortcutManager.class
                );

        if (manager == null
                || !manager.isRequestPinShortcutSupported()) {
            return false;
        }

        Intent intent =
                new Intent(
                        context,
                        JarvisDialerActivity.class
                );

        intent.setAction(
                Intent.ACTION_VIEW
        );

        ShortcutInfo shortcut =
                new ShortcutInfo.Builder(
                        context,
                        SHORTCUT_ID
                )
                        .setShortLabel(
                                "JARVIS Phone"
                        )
                        .setLongLabel(
                                "JARVIS Phone"
                        )
                        .setIcon(
                                Icon.createWithResource(
                                        context,
                                        android.R.drawable
                                                .sym_action_call
                                )
                        )
                        .setIntent(intent)
                        .build();

        PendingIntent callback =
                PendingIntent.getBroadcast(
                        context,
                        7311,
                        new Intent(
                                "com.jarvis.companion."
                                        + "PHONE_SHORTCUT_PINNED"
                        ).setPackage(
                                context.getPackageName()
                        ),
                        PendingIntent.FLAG_UPDATE_CURRENT
                                | PendingIntent.FLAG_IMMUTABLE
                );

        return manager.requestPinShortcut(
                shortcut,
                callback.getIntentSender()
        );
    }
}
