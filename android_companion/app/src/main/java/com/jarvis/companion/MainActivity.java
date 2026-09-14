package com.jarvis.companion;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.util.Base64;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class MainActivity extends Activity {
    private static final int REQ_CORE_PERMISSIONS = 2901;
    private static final int REQ_MIC_ONLY = 2902;
    private EditText serverUrl, fallbackIp, pairCode, askText;
    private TextView status, jarvisReply;
    private PhoneApiClient api;
    private TextToSpeech tts;
    private boolean voiceReplies = true;
    private boolean pendingVoiceAfterPermission = false;
    private final LocalVoiceRecorder voiceRecorder = new LocalVoiceRecorder();

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        api = new PhoneApiClient(this);
        serverUrl = findViewById(R.id.serverUrl);
        fallbackIp = findViewById(R.id.fallbackIp);
        pairCode = findViewById(R.id.pairCode);
        askText = findViewById(R.id.askText);
        jarvisReply = findViewById(R.id.jarvisReply);
        status = findViewById(R.id.statusText);
        serverUrl.setText(api.prefs().getString("server_url", ""));
        fallbackIp.setText(api.prefs().getString("tailscale_ipv4", ""));
        voiceReplies = api.prefs().getBoolean("voice_replies", true);
        tts = new TextToSpeech(this, code -> { if (code == TextToSpeech.SUCCESS) tts.setLanguage(Locale.US); });

        findViewById(R.id.testConnectionButton).setOnClickListener(v -> testConnection());
        findViewById(R.id.pairButton).setOnClickListener(v -> pair());
        findViewById(R.id.startButton).setOnClickListener(v -> startLink());
        findViewById(R.id.askButton).setOnClickListener(v -> askJarvis());
        findViewById(R.id.voiceAskButton).setOnClickListener(v -> toggleLocalVoiceQuestion());
        findViewById(R.id.voiceReplyButton).setOnClickListener(v -> {
            voiceReplies = !voiceReplies;
            api.prefs().edit().putBoolean("voice_replies", voiceReplies).apply();
            updateVoiceButton();
        });
        findViewById(R.id.stopButton).setOnClickListener(v -> {
            api.prefs().edit().putBoolean("companion_enabled", false).apply();
            stopService(new Intent(this, JarvisForegroundService.class));
            setStatus("Background companion stopped.");
        });
        updateVoiceButton();
        updateStatus();

        // V29.1: permissions use normal Android runtime prompts instead of ugly
        // one-off buttons in the JARVIS UI. Call-log permission is optional and
        // can be refused by Android on non-dialer/sideloaded apps.
        if (!api.prefs().getBoolean("permission_onboarding_shown", false)) {
            ensureCorePermissions();
            api.prefs().edit().putBoolean("permission_onboarding_shown", true).apply();
        }
    }

    private String server() { return serverUrl.getText().toString().trim(); }
    private String fallback() { return fallbackIp.getText().toString().trim(); }

    private void ensureCorePermissions() {
        List<String> wanted = new ArrayList<>();
        addIfMissing(wanted, Manifest.permission.READ_CALENDAR);
        addIfMissing(wanted, Manifest.permission.READ_CONTACTS);
        addIfMissing(wanted, Manifest.permission.CALL_PHONE);
        addIfMissing(wanted, Manifest.permission.RECORD_AUDIO);
        addIfMissing(wanted, Manifest.permission.READ_CALL_LOG);
        if (Build.VERSION.SDK_INT >= 33) addIfMissing(wanted, Manifest.permission.POST_NOTIFICATIONS);
        if (!wanted.isEmpty()) requestPermissions(wanted.toArray(new String[0]), REQ_CORE_PERMISSIONS);
    }

    private void addIfMissing(List<String> list, String permission) {
        if (checkSelfPermission(permission) != PackageManager.PERMISSION_GRANTED) list.add(permission);
    }

    private void testConnection() {
        final String u = server(), ip = fallback();
        setStatus("Testing private JARVIS connection…");
        new Thread(() -> {
            try {
                JSONObject r = api.health(u, ip);
                api.prefs().edit().putString("server_url", u).putString("tailscale_ipv4", ip).apply();
                runOnUiThread(() -> setStatus("Connection OK. JARVIS " + r.optString("build", "v" + r.optInt("version", 0)) + " is reachable."));
            } catch (Exception ex) {
                runOnUiThread(() -> setStatus("Connection test failed: " + ex.getMessage()));
            }
        }, "jarvis-health").start();
    }

    private void pair() {
        final String u = server(), ip = fallback(), code = pairCode.getText().toString().trim();
        setStatus("Pairing…");
        new Thread(() -> {
            try {
                api.health(u, ip);
                JSONObject r = api.pair(u, ip, code);
                runOnUiThread(() -> {
                    setStatus("Paired securely as " + r.optString("name", "phone") + ". Remote JARVIS is ready.");
                    ensureCorePermissions();
                });
            } catch (Exception ex) {
                runOnUiThread(() -> setStatus("Pairing failed: " + ex.getMessage()));
            }
        }, "jarvis-pair").start();
    }

    private void startLink() {
        if (api.prefs().getString("device_id", "").isEmpty()) {
            setStatus("Pair the phone first.");
            return;
        }
        ensureCorePermissions();
        api.prefs().edit().putBoolean("companion_enabled", true).apply();
        startForegroundService(new Intent(this, JarvisForegroundService.class));
        setStatus("Secure background link started. Remote JARVIS is ready while the PC core is online.");
    }

    private void askJarvis() {
        final String q = askText.getText().toString().trim();
        if (q.isEmpty()) { setStatus("Type or dictate a question first."); return; }
        if (api.prefs().getString("device_id", "").isEmpty()) { setStatus("Pair the phone first."); return; }
        jarvisReply.setText("JARVIS is thinking…");
        new Thread(() -> {
            try {
                JSONObject body = new JSONObject(); body.put("text", q);
                JSONObject r = api.signedPost("/api/phone/ask", body, 90000);
                String answer = r.optString("text", r.optString("spoken_text", ""));
                if (!r.optBoolean("ok", false)) throw new IllegalStateException(r.optString("error", "JARVIS returned an error."));
                runOnUiThread(() -> showAnswer(answer));
            } catch (Exception ex) {
                runOnUiThread(() -> jarvisReply.setText("Remote JARVIS failed: " + ex.getMessage()));
            }
        }, "jarvis-remote-ask").start();
    }

    private void toggleLocalVoiceQuestion() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            pendingVoiceAfterPermission = true;
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_MIC_ONLY);
            return;
        }
        Button button = findViewById(R.id.voiceAskButton);
        if (!voiceRecorder.isActive()) {
            try {
                voiceRecorder.start();
                button.setText("STOP & SEND");
                setStatus("Listening locally… tap STOP & SEND when finished. Audio is transcribed by JARVIS on your PC, not Google Voice.");
            } catch (Exception ex) {
                setStatus("Phone microphone failed: " + ex.getMessage());
            }
            return;
        }
        button.setEnabled(false);
        button.setText("TRANSCRIBING…");
        new Thread(() -> {
            try {
                byte[] wav = voiceRecorder.stopToWav();
                if (wav.length == 0) throw new IllegalStateException("No usable speech was recorded.");
                JSONObject body = new JSONObject();
                body.put("format", "wav");
                body.put("audio_b64", Base64.encodeToString(wav, Base64.NO_WRAP));
                JSONObject r = api.signedPost("/api/phone/voice", body, 120000);
                if (!r.optBoolean("ok", false)) throw new IllegalStateException(r.optString("error", "Voice request failed."));
                String transcript = r.optString("transcript", "");
                String answer = r.optString("text", r.optString("spoken_text", ""));
                runOnUiThread(() -> {
                    askText.setText(transcript);
                    showAnswer(answer);
                    button.setText("TAP TO TALK");
                    button.setEnabled(true);
                    setStatus("Local JARVIS voice transcription complete.");
                });
            } catch (Exception ex) {
                runOnUiThread(() -> {
                    button.setText("TAP TO TALK");
                    button.setEnabled(true);
                    setStatus("Voice request failed: " + ex.getMessage());
                });
            }
        }, "jarvis-local-voice").start();
    }

    private void showAnswer(String answer) {
        jarvisReply.setText(answer);
        if (voiceReplies && tts != null && answer != null && !answer.isEmpty()) {
            tts.speak(answer, TextToSpeech.QUEUE_FLUSH, null, "jarvis-phone-reply");
        }
    }

    private void updateVoiceButton() {
        ((Button)findViewById(R.id.voiceReplyButton)).setText("PHONE VOICE REPLIES: " + (voiceReplies ? "ON" : "OFF"));
        ((Button)findViewById(R.id.voiceAskButton)).setText(voiceRecorder.isActive() ? "STOP & SEND" : "TAP TO TALK");
    }

    private void updateStatus() {
        String device = api.prefs().getString("device_id", "");
        boolean cal = checkSelfPermission(Manifest.permission.READ_CALENDAR) == PackageManager.PERMISSION_GRANTED;
        boolean contacts = checkSelfPermission(Manifest.permission.READ_CONTACTS) == PackageManager.PERMISSION_GRANTED;
        boolean calling = checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED;
        boolean mic = checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
        boolean history = checkSelfPermission(Manifest.permission.READ_CALL_LOG) == PackageManager.PERMISSION_GRANTED;
        if (device.isEmpty()) {
            setStatus("Not paired. Enter the secure HTTPS *.ts.net URL from JARVIS. Permissions are requested through normal Android prompts.");
        } else {
            setStatus("Paired: " + device
                    + "\nCalendar: " + yes(cal)
                    + " · Contacts: " + yes(contacts)
                    + " · Calling: " + yes(calling)
                    + "\nLocal JARVIS microphone: " + yes(mic)
                    + " · Full call history: " + (history ? "GRANTED" : "LIMITED")
                    + "\nRemote JARVIS: READY when the PC core is online.");
        }
    }

    private String yes(boolean value) { return value ? "GRANTED" : "NOT GRANTED"; }
    private void setStatus(String s) { status.setText(s); }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        updateStatus();
        if (requestCode == REQ_MIC_ONLY && checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED && pendingVoiceAfterPermission) {
            pendingVoiceAfterPermission = false;
            toggleLocalVoiceQuestion();
        }
    }

    @Override protected void onDestroy() {
        try { if (voiceRecorder.isActive()) voiceRecorder.stopToWav(); } catch (Exception ignored) {}
        if (tts != null) { tts.stop(); tts.shutdown(); }
        super.onDestroy();
    }
}
