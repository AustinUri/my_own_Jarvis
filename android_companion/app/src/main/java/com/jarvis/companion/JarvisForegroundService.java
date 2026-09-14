package com.jarvis.companion;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.BatteryManager;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;

import org.json.JSONObject;

public final class JarvisForegroundService extends Service {
    public static final String CHANNEL = "jarvis_companion_link";
    private static final int NOTIFICATION_ID = 2601;
    private volatile boolean running;
    private Thread worker;

    @Override public void onCreate() {
        super.onCreate();
        createChannel();
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        Notification n = new Notification.Builder(this, CHANNEL)
                .setContentTitle("JARVIS Companion active")
                .setContentText("Secure phone link is connected through your private tailnet.")
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setOngoing(true)
                .build();
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(NOTIFICATION_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_REMOTE_MESSAGING);
        } else {
            startForeground(NOTIFICATION_ID, n);
        }
        if (!running) {
            running = true;
            worker = new Thread(this::loop, "jarvis-companion-poll");
            worker.start();
        }
        return START_STICKY;
    }

    private void loop() {
        PhoneApiClient api = new PhoneApiClient(this);
        long backoff = 1000;
        while (running) {
            try {
                JSONObject cmd = api.signedPost("/api/phone/poll", new JSONObject(), 35000);
                String name = cmd.optString("command", "noop");
                String id = cmd.optString("command_id", "");
                if (!"noop".equals(name) && !id.isEmpty()) {
                    JSONObject result = execute(name, cmd.optJSONObject("args"));
                    api.signedPost("/api/phone/result/" + id, result, 12000);
                }
                backoff = 1000;
            } catch (Exception ex) {
                try { Thread.sleep(backoff); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
                backoff = Math.min(30000, backoff * 2);
            }
        }
    }

    private JSONObject execute(String command, JSONObject args) {
        JSONObject out = new JSONObject();
        try {
            if ("calendar_list".equals(command)) {
                int days = args == null ? 3 : args.optInt("days", 3);
                out.put("ok", true);
                out.put("events", CalendarBridge.upcoming(this, days));
            } else if ("device_info".equals(command)) {
                JSONObject info = new JSONObject();
                info.put("manufacturer", Build.MANUFACTURER);
                info.put("model", Build.MODEL);
                info.put("android", Build.VERSION.RELEASE);
                info.put("sdk", Build.VERSION.SDK_INT);
                out.put("ok", true);
                out.put("device", info);
            } else if ("battery_status".equals(command)) {
                BatteryManager bm = (BatteryManager)getSystemService(BATTERY_SERVICE);
                int pct = bm == null ? -1 : bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
                boolean charging = bm != null && Build.VERSION.SDK_INT >= 23 && bm.isCharging();
                out.put("ok", true);
                out.put("battery_percent", pct);
                out.put("charging", charging);
            } else if ("contact_search".equals(command)) {
                String query = args == null ? "" : args.optString("query", "");
                out.put("ok", true);
                out.put("contacts", ContactsBridge.search(this, query));
            } else if ("call_log_list".equals(command)) {
                int limit = args == null ? 30 : args.optInt("limit", 30);
                out.put("ok", true);
                out.put("calls", CallLogBridge.recent(this, limit));
                out.put("full_history", CallLogBridge.hasFullAccess(this));
                out.put("history_source", CallLogBridge.hasFullAccess(this) ? "android_call_log" : "jarvis_calls_only");
            } else if ("call_number".equals(command)) {
                String number = args == null ? "" : args.optString("number", "");
                String name = args == null ? "" : args.optString("name", "");
                return ContactsBridge.call(this, number, name);
            } else {
                out.put("ok", false);
                out.put("error", "Unsupported command. This v29.1 companion exposes only approved capabilities.");
            }
        } catch (Exception ex) {
            try {
                out.put("ok", false);
                out.put("error", ex.getMessage() == null ? ex.getClass().getSimpleName() : ex.getMessage());
            } catch (Exception ignored) {}
        }
        return out;
    }

    @Override public void onDestroy() {
        running = false;
        if (worker != null) worker.interrupt();
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent intent) { return null; }

    private void createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(CHANNEL, "JARVIS secure link", NotificationManager.IMPORTANCE_LOW);
            ch.setDescription("Shows when the JARVIS phone companion is actively connected.");
            getSystemService(NotificationManager.class).createNotificationChannel(ch);
        }
    }
}
