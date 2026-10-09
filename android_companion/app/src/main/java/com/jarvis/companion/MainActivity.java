package com.jarvis.companion;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.speech.RecognizerIntent;
import android.speech.tts.TextToSpeech;
import android.widget.EditText;
import android.widget.Switch;
import android.widget.TextView;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class MainActivity extends Activity {

    private static final int REQ_CORE_PERMISSIONS = 3001;
    private static final int REQ_VOICE_INPUT = 3002;

    private PhoneApiClient api;
    private EditText pairCode;
    private EditText askText;
    private TextView status;
    private TextView jarvisReply;
    private Switch voiceReplySwitch;
    private TextToSpeech tts;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_main);

        api = new PhoneApiClient(this);
        pairCode = findViewById(R.id.pairCode);
        askText = findViewById(R.id.askText);
        status = findViewById(R.id.statusText);
        jarvisReply = findViewById(R.id.jarvisReply);
        voiceReplySwitch = findViewById(R.id.voiceReplySwitch);

        findViewById(R.id.testConnectionButton)
                .setOnClickListener(v -> testCloud());

        findViewById(R.id.pairButton)
                .setOnClickListener(v -> pair());

        findViewById(R.id.askButton)
                .setOnClickListener(v -> askJarvis(
                        askText.getText().toString()
                ));

        findViewById(R.id.voiceAskButton)
                .setOnClickListener(v -> startVoiceInput());

        boolean voiceReplies = api.prefs()
                .getBoolean("voice_replies_enabled", true);

        voiceReplySwitch.setChecked(voiceReplies);
        voiceReplySwitch.setOnCheckedChangeListener((buttonView, isChecked) ->
                api.prefs()
                        .edit()
                        .putBoolean("voice_replies_enabled", isChecked)
                        .apply());

        tts = new TextToSpeech(this, statusCode -> {
            if (statusCode == TextToSpeech.SUCCESS) {
                tts.setLanguage(Locale.getDefault());
            }
        });

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

    private void askJarvis(String text) {
        String clean = text == null ? "" : text.trim();
        if (clean.isEmpty()) {
            jarvisReply.setText("Enter a message for JARVIS.");
            return;
        }

        if (!api.isPaired()) {
            jarvisReply.setText("Pair the Samsung with JARVIS Cloud first.");
            return;
        }

        jarvisReply.setText("JARVIS is thinking…");
        askText.setText("");

        new Thread(() -> {
            try {
                JSONObject result = api.askJarvis(clean);
                String reply = result.optString("text", "").trim();
                if (reply.isEmpty()) {
                    reply = "JARVIS returned no text response.";
                }

                final String answer = reply;
                runOnUiThread(() -> {
                    jarvisReply.setText(answer);
                    if (voiceReplySwitch.isChecked() && tts != null) {
                        tts.speak(
                                answer,
                                TextToSpeech.QUEUE_FLUSH,
                                null,
                                "jarvis-v30-reply"
                        );
                    }
                });

            } catch (Exception ex) {
                runOnUiThread(() ->
                        jarvisReply.setText(
                                "JARVIS request failed:\n" + ex.getMessage()
                        ));
            }
        }, "jarvis-mobile-chat").start();
    }

    private void startVoiceInput() {
        ensurePermissions();

        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
        );
        intent.putExtra(
                RecognizerIntent.EXTRA_LANGUAGE,
                Locale.getDefault().toLanguageTag()
        );
        intent.putExtra(
                RecognizerIntent.EXTRA_PROMPT,
                "Speak to JARVIS"
        );

        try {
            startActivityForResult(intent, REQ_VOICE_INPUT);
        } catch (Exception ex) {
            jarvisReply.setText(
                    "Voice recognition is unavailable:\n" + ex.getMessage()
            );
        }
    }

    @Override
    protected void onActivityResult(
            int requestCode,
            int resultCode,
            Intent data
    ) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode != REQ_VOICE_INPUT || resultCode != RESULT_OK || data == null) {
            return;
        }

        ArrayList<String> matches = data.getStringArrayListExtra(
                RecognizerIntent.EXTRA_RESULTS
        );

        if (matches == null || matches.isEmpty()) {
            return;
        }

        String transcript = matches.get(0);
        askText.setText(transcript);
        askJarvis(transcript);
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

    @Override
    protected void onDestroy() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
            tts = null;
        }
        super.onDestroy();
    }
}
