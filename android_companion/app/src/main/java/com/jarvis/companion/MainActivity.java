package com.jarvis.companion;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.widget.EditText;
import android.widget.Switch;
import android.widget.TextView;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

public final class MainActivity extends Activity {

    private static final int REQ_CORE_PERMISSIONS = 3001;

    private PhoneApiClient api;
    private EditText pairCode;
    private TextView status;
    private Switch voiceReplySwitch;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_main);

        api = new PhoneApiClient(this);
        pairCode = findViewById(R.id.pairCode);
        status = findViewById(R.id.statusText);
        voiceReplySwitch = findViewById(R.id.voiceReplySwitch);

        findViewById(R.id.testConnectionButton)
                .setOnClickListener(v -> testCloud());

        findViewById(R.id.pairButton)
                .setOnClickListener(v -> pair());

        boolean voiceReplies = api.prefs()
                .getBoolean("voice_replies_enabled", true);

        voiceReplySwitch.setChecked(voiceReplies);
        voiceReplySwitch.setOnCheckedChangeListener((buttonView, isChecked) ->
                api.prefs()
                        .edit()
                        .putBoolean("voice_replies_enabled", isChecked)
                        .apply());

        ensurePermissions();
        updateStatus();

        // V30 is cloud-first. Once paired, the Samsung should not depend on the PC
        // or on a manual Start Link button.
        if (api.isPaired()) {
            startCloudLink();
        }
    }

    private void testCloud() {
        setStatus("Testing JARVIS Cloud…");

        new Thread(() -> {
            try {
                JSONObject result = api.health();

                runOnUiThread(() ->
                        setStatus(
                                "JARVIS Cloud ONLINE\n" +
                                result.optString("service", "jarvis-cloud-core") +
                                "\nVersion: " + result.optString("version", "V30") +
                                "\nPaired: " + (api.isPaired() ? "YES" : "NO")
                        ));

            } catch (Exception ex) {
                runOnUiThread(() ->
                        setStatus(
                                "Cloud connection failed:\n" +
                                ex.getMessage()
                        ));
            }
        }, "jarvis-cloud-test").start();
    }

    private void pair() {
        String code = pairCode.getText().toString().trim();
        setStatus("Pairing Samsung with JARVIS Cloud…");

        new Thread(() -> {
            try {
                JSONObject result = api.pair(code);

                runOnUiThread(() -> {
                    setStatus(
                            "Paired successfully.\n" +
                            "Device: " + result.optString(
                                    "device_id",
                                    PhoneApiClient.DEVICE_ID
                            ) +
                            "\nStarting Oracle Device Bus…"
                    );

                    ensurePermissions();
                    startCloudLink();
                });

            } catch (Exception ex) {
                runOnUiThread(() ->
                        setStatus(
                                "Pairing failed:\n" +
                                ex.getMessage()
                        ));
            }
        }, "jarvis-cloud-pair").start();
    }

    private void startCloudLink() {
        if (!api.isPaired()) {
            return;
        }

        ensurePermissions();

        api.prefs()
                .edit()
                .putBoolean("companion_enabled", true)
                .apply();

        Intent service = new Intent(
                this,
                JarvisForegroundService.class
        );

        if (Build.VERSION.SDK_INT >= 26) {
            startForegroundService(service);
        } else {
            startService(service);
        }
    }

    private void ensurePermissions() {
        List<String> wanted = new ArrayList<>();

        addIfMissing(wanted, Manifest.permission.READ_CALENDAR);
        addIfMissing(wanted, Manifest.permission.READ_CONTACTS);
        addIfMissing(wanted, Manifest.permission.CALL_PHONE);
        addIfMissing(wanted, Manifest.permission.RECORD_AUDIO);
        addIfMissing(wanted, Manifest.permission.READ_CALL_LOG);

        if (Build.VERSION.SDK_INT >= 33) {
            addIfMissing(wanted, Manifest.permission.POST_NOTIFICATIONS);
        }

        if (!wanted.isEmpty()) {
            requestPermissions(
                    wanted.toArray(new String[0]),
                    REQ_CORE_PERMISSIONS
            );
        }
    }

    private void addIfMissing(
            List<String> list,
            String permission
    ) {
        if (checkSelfPermission(permission)
                != PackageManager.PERMISSION_GRANTED) {
            list.add(permission);
        }
    }

    private void updateStatus() {
        if (api.isPaired()) {
            boolean connected = api.prefs()
                    .getBoolean("cloud_connected", false);

            setStatus(
                    "JARVIS V30\n" +
                    "Cloud: " + PhoneApiClient.CLOUD +
                    "\nDevice: " + PhoneApiClient.DEVICE_ID +
                    "\nPaired: YES" +
                    "\nDevice Bus: " + (connected ? "ONLINE" : "CONNECTING")
            );
        } else {
            setStatus("JARVIS V30 Cloud is not paired yet.");
        }
    }

    private void setStatus(String text) {
        status.setText(text);
    }
}
