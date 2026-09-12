package com.jarvis.companion;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import org.json.JSONObject;

public final class MainActivity extends Activity {
    private static final int REQ_CALENDAR = 2602;
    private static final int REQ_NOTIFICATIONS = 2603;
    private EditText serverUrl;
    private EditText pairCode;
    private TextView status;
    private PhoneApiClient api;

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        api = new PhoneApiClient(this);
        serverUrl = findViewById(R.id.serverUrl);
        pairCode = findViewById(R.id.pairCode);
        status = findViewById(R.id.statusText);
        serverUrl.setText(api.prefs().getString("server_url", ""));

        ((Button)findViewById(R.id.pairButton)).setOnClickListener(v -> pair());
        ((Button)findViewById(R.id.calendarPermissionButton)).setOnClickListener(v -> requestPermissions(new String[]{Manifest.permission.READ_CALENDAR}, REQ_CALENDAR));
        ((Button)findViewById(R.id.startButton)).setOnClickListener(v -> startLink());
        ((Button)findViewById(R.id.stopButton)).setOnClickListener(v -> {
            stopService(new Intent(this, JarvisForegroundService.class));
            setStatus("Companion stopped. JARVIS cannot access phone data while it is stopped.");
        });
        updateStatus();
    }

    private void pair() {
        final String url = serverUrl.getText().toString().trim();
        final String code = pairCode.getText().toString().trim();
        setStatus("Pairing…");
        new Thread(() -> {
            try {
                JSONObject r = api.pair(url, code);
                runOnUiThread(() -> setStatus("Paired securely as " + r.optString("name", "phone") + ". Now grant calendar read access, then start the companion."));
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
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQ_NOTIFICATIONS);
        }
        startForegroundService(new Intent(this, JarvisForegroundService.class));
        setStatus("Secure companion started. A persistent notification remains visible while the link is active.");
    }

    private void updateStatus() {
        String device = api.prefs().getString("device_id", "");
        boolean cal = checkSelfPermission(Manifest.permission.READ_CALENDAR) == PackageManager.PERMISSION_GRANTED;
        if (device.isEmpty()) setStatus("Not paired. Install/sign in to Tailscale first, then use the server URL and pairing code shown by JARVIS on the PC.");
        else setStatus("Paired: " + device + "\nNative calendar read permission: " + (cal ? "GRANTED" : "NOT GRANTED") + "\nStart the companion when you want Jarvis to use the phone calendar.");
    }

    private void setStatus(String text) { status.setText(text); }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        updateStatus();
    }
}
