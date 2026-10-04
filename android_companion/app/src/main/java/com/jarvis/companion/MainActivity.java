package com.jarvis.companion;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.widget.EditText;
import android.widget.TextView;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

public final class MainActivity extends Activity {

    private static final int REQ_CORE_PERMISSIONS = 3001;

    private PhoneApiClient api;
    private EditText pairCode;
    private TextView status;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_main);

        api = new PhoneApiClient(this);

        pairCode = findViewById(R.id.pairCode);
        status = findViewById(R.id.statusText);

        findViewById(R.id.testConnectionButton)
                .setOnClickListener(v -> testCloud());

        findViewById(R.id.pairButton)
                .setOnClickListener(v -> pair());

        findViewById(R.id.startButton)
                .setOnClickListener(v -> startCloudLink());

        findViewById(R.id.stopButton)
                .setOnClickListener(v -> {
                    api.prefs()
                            .edit()
                            .putBoolean(
                                    "companion_enabled",
                                    false
                            )
                            .apply();

                    stopService(
                            new Intent(
                                    this,
                                    JarvisForegroundService.class
                            )
                    );

                    setStatus(
                            "JARVIS Cloud background link stopped."
                    );
                });

        /*
         * AI question routing will be connected after
         * Samsung is successfully online in Device Bus.
         */
        findViewById(R.id.askButton)
                .setOnClickListener(v ->
                        setStatus(
                                "Samsung is being migrated to V30 Cloud. " +
                                "Remote AI routing is the next stage."
                        ));

        findViewById(R.id.voiceAskButton)
                .setOnClickListener(v ->
                        setStatus(
                                "Cloud voice routing will be enabled after " +
                                "Samsung Device Bus pairing is verified."
                        ));

        findViewById(R.id.voiceReplyButton)
                .setOnClickListener(v ->
                        setStatus(
                                "Phone voice replies will return with " +
                                "the V30 AI routing stage."
                        ));

        ensurePermissions();
        updateStatus();
    }

    private void testCloud() {

        setStatus("Testing JARVIS Cloud…");

        new Thread(() -> {
            try {

                JSONObject result = api.health();

                runOnUiThread(() ->
                        setStatus(
                                "JARVIS Cloud ONLINE\n" +
                                result.optString(
                                        "service",
                                        "jarvis-cloud-core"
                                ) +
                                "\nVersion: " +
                                result.optString(
                                        "version",
                                        "V30"
                                )
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

        String code =
                pairCode.getText().toString().trim();

        setStatus("Pairing Samsung with JARVIS Cloud…");

        new Thread(() -> {

            try {

                JSONObject result = api.pair(code);

                runOnUiThread(() -> {

                    setStatus(
                            "Paired successfully.\n" +
                            "Device: " +
                            result.optString(
                                    "device_id",
                                    PhoneApiClient.DEVICE_ID
                            ) +
                            "\nJARVIS Cloud is ready."
                    );

                    ensurePermissions();
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

            setStatus(
                    "Pair the Samsung with JARVIS Cloud first."
            );

            return;
        }

        ensurePermissions();

        api.prefs()
                .edit()
                .putBoolean(
                        "companion_enabled",
                        true
                )
                .apply();

        Intent service =
                new Intent(
                        this,
                        JarvisForegroundService.class
                );

        if (Build.VERSION.SDK_INT >= 26) {
            startForegroundService(service);
        } else {
            startService(service);
        }

        setStatus(
                "Starting secure JARVIS V30 Cloud link…"
        );
    }

    private void ensurePermissions() {

        List<String> wanted = new ArrayList<>();

        addIfMissing(
                wanted,
                Manifest.permission.READ_CALENDAR
        );

        addIfMissing(
                wanted,
                Manifest.permission.READ_CONTACTS
        );

        addIfMissing(
                wanted,
                Manifest.permission.CALL_PHONE
        );

        addIfMissing(
                wanted,
                Manifest.permission.RECORD_AUDIO
        );

        addIfMissing(
                wanted,
                Manifest.permission.READ_CALL_LOG
        );

        if (Build.VERSION.SDK_INT >= 33) {
            addIfMissing(
                    wanted,
                    Manifest.permission.POST_NOTIFICATIONS
            );
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

            setStatus(
                    "JARVIS V30\n" +
                    "Cloud: " + PhoneApiClient.CLOUD +
                    "\nDevice: " + PhoneApiClient.DEVICE_ID +
                    "\nPaired: YES"
            );

        } else {

            setStatus(
                    "JARVIS V30 Cloud is not paired yet."
            );
        }
    }

    private void setStatus(String text) {
        status.setText(text);
    }
}
