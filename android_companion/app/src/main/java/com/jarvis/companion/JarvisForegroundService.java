package com.jarvis.companion;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import android.content.Intent;

import org.json.JSONObject;

import java.util.concurrent.TimeUnit;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

public final class JarvisForegroundService extends Service {

    public static final String ACTION_PHONE_STATE_EVENT =
            "com.jarvis.companion.PHONE_STATE_EVENT";

    public static final String ACTION_WHATSAPP_CALL_EVENT =
            "com.jarvis.companion.WHATSAPP_CALL_EVENT";

    public static final String CHANNEL =
            "jarvis_cloud_link";

    private static final int NOTIFICATION_ID = 3001;

    private volatile boolean running;

    private WebSocket socket;

    // PHASE_2_2_LIVE_CALL_REACTION
    private android.speech.tts.TextToSpeech callTts;
    private volatile boolean callTtsReady = false;
    private volatile String pendingCallSpeech = null;

    private final android.os.Handler callReactionHandler =
            new android.os.Handler(
                    android.os.Looper.getMainLooper()
            );

    private Runnable pendingCallAnnouncement;
    private String pendingCallerName = "";
    private String pendingCallerNumber = "";
    private String lastAnnouncedCallKey = "";
    private long lastAnnouncedCallAtMs = 0L;


    private final OkHttpClient client =
            new OkHttpClient.Builder()
                    .pingInterval(
                            20,
                            TimeUnit.SECONDS
                    )
                    .retryOnConnectionFailure(true)
                    .build();

    @Override
    public void onCreate() {
        super.onCreate();
        createChannel();
    }

    @Override
    public int onStartCommand(
            Intent intent,
            int flags,
            int startId
    ) {

        Notification notification =
                new Notification.Builder(
                        this,
                        CHANNEL
                )
                        .setContentTitle(
                                "JARVIS V30"
                        )
                        .setContentText(
                                "Connected to Oracle Device Bus"
                        )
                        .setSmallIcon(
                                android.R.drawable.stat_notify_sync
                        )
                        .setOngoing(true)
                        .build();

        if (Build.VERSION.SDK_INT >= 34) {

            startForeground(
                    NOTIFICATION_ID,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_REMOTE_MESSAGING
            );

        } else {

            startForeground(
                    NOTIFICATION_ID,
                    notification
            );
        }

        if (!running) {

            running = true;
            connect();
        }

        if (intent != null
                && ACTION_PHONE_STATE_EVENT.equals(intent.getAction())) {
            sendPhoneStateEvent(intent);
                    handleLiveCallReaction(intent, false);
        }

        if (intent != null
                && ACTION_WHATSAPP_CALL_EVENT.equals(intent.getAction())) {
            handleLiveCallReaction(intent, true);
        }

        return START_STICKY;
    }

    private void connect() {

        if (!running) return;

        try {

            PhoneApiClient api =
                    new PhoneApiClient(this);

            String token =
                    api.deviceToken();

            if (token.isEmpty()) {
                stopSelf();
                return;
            }

            String url =
                    "wss://uri-jarvis.duckdns.org" +
                    "/api/v1/ws/" +
                    PhoneApiClient.DEVICE_ID +
                    "?device_type=android";

            Request request =
                    new Request.Builder()
                            .url(url)
                            .header(
                                    "Authorization",
                                    "Bearer " + token
                            )
                            .build();

            socket = client.newWebSocket(
                    request,
                    new WebSocketListener() {

                        @Override
                        public void onOpen(
                                WebSocket webSocket,
                                Response response
                        ) {

                            getSharedPreferences(
                                    PhoneApiClient.PREFS,
                                    MODE_PRIVATE
                            )
                                    .edit()
                                    .putBoolean(
                                            "cloud_connected",
                                            true
                                    )
                                    .apply();

                            webSocket.send("ping");
                            flushQueuedDeviceEvents(webSocket);
                        }

                        @Override
                        public void onMessage(
                                WebSocket webSocket,
                                String text
                        ) {

                            try {

                                JSONObject message =
                                        new JSONObject(text);

                                String type =
                                        message.optString(
                                                "type",
                                                ""
                                        );

                                if ("welcome".equals(type)) {
                                    webSocket.send("ping");
                                    return;
                                }

                                if ("caller_intelligence_result".equals(type)) {
                                    handleCallerIntelligenceResult(message);
                                    return;
                                }

                                if ("job".equals(type)) {
                                    handleJob(webSocket, message);
                                }

                            } catch (Exception ignored) {
                            }
                        }

                        @Override
                        public void onClosed(
                                WebSocket webSocket,
                                int code,
                                String reason
                        ) {

                            markDisconnected();
                            reconnectLater();
                        }

                        @Override
                        public void onFailure(
                                WebSocket webSocket,
                                Throwable t,
                                Response response
                        ) {

                            markDisconnected();
                            reconnectLater();
                        }
                    }
            );

        } catch (Exception ex) {

            markDisconnected();
            reconnectLater();
        }
    }

    private void handleJob(
            WebSocket webSocket,
            JSONObject message
    ) {

        final String jobId =
                message.optString("job_id", "");

        final String jobType =
                message.optString("job_type", "");

        JSONObject suppliedPayload =
                message.optJSONObject("payload");

        final JSONObject payload =
                suppliedPayload == null
                        ? new JSONObject()
                        : suppliedPayload;

        new Thread(() -> {

            JSONObject reply =
                    new JSONObject();

            try {

                reply.put(
                        "type",
                        "job_result"
                );

                reply.put(
                        "job_id",
                        jobId
                );

                reply.put(
                        "device_id",
                        PhoneApiClient.DEVICE_ID
                );

                JSONObject result =
                        executePhoneJob(
                                jobType,
                                payload
                        );

                reply.put(
                        "ok",
                        true
                );

                reply.put(
                        "result",
                        result
                );

            } catch (Exception ex) {

                try {
                    reply.put(
                            "type",
                            "job_result"
                    );

                    reply.put(
                            "job_id",
                            jobId
                    );

                    reply.put(
                            "device_id",
                            PhoneApiClient.DEVICE_ID
                    );

                    reply.put(
                            "ok",
                            false
                    );

                    String messageText =
                            ex.getMessage();

                    if (
                            messageText == null
                            || messageText.trim().isEmpty()
                    ) {
                        messageText =
                                ex.getClass()
                                        .getSimpleName();
                    }

                    reply.put(
                            "error",
                            messageText
                    );

                } catch (Exception ignored) {
                }
            }

            webSocket.send(
                    reply.toString()
            );

        }, "jarvis-phone-job").start();
    }


    private JSONObject executePhoneJob(
            String jobType,
            JSONObject payload
    ) throws Exception {

        JSONObject out =
                new JSONObject();

        switch (jobType) {

            case "phone.capabilities":

                out.put(
                        "calendar",
                        true
                );

                out.put(
                        "contacts",
                        true
                );

                out.put(
                        "call_history",
                        true
                );

                out.put(
                        "cellular_call",
                        true
                );

                out.put(
                        "whatsapp_compose",
                        true
                );

                out.put(
                        "whatsapp_auto_send",
                        false
                );

                                out.put(
                        "reminder_alarm",
                        true
                );

return out;


            case "phone.calendar_upcoming":

                int days =
                        payload.optInt(
                                "days",
                                7
                        );

                out.put(
                        "events",
                        CalendarBridge.upcoming(
                                this,
                                days
                        )
                );

                return out;


            case "phone.contacts_search":

                String query =
                        payload.optString(
                                "query",
                                ""
                        );

                out.put(
                        "contacts",
                        ContactsBridge.search(
                                this,
                                query
                        )
                );

                return out;


            case "phone.call_history":

                int limit =
                        payload.optInt(
                                "limit",
                                20
                        );

                out.put(
                        "calls",
                        CallLogBridge.recent(
                                this,
                                limit
                        )
                );

                out.put(
                        "full_history",
                        CallLogBridge.hasFullAccess(
                                this
                        )
                );

                out.put(
                        "history_source",
                        CallLogBridge.hasFullAccess(
                                this
                        )
                                ? "android_call_log"
                                : "jarvis_calls_only"
                );

                return out;


            case "phone.call":

                return ContactsBridge.call(
                        this,
                        payload.optString(
                                "number",
                                ""
                        ),
                        payload.optString(
                                "name",
                                ""
                        )
                );


            case "phone.whatsapp_compose":

                return WhatsAppBridge.compose(
                        this,
                        payload.optString(
                                "number",
                                ""
                        ),
                        payload.optString(
                                "name",
                                ""
                        ),
                        payload.optString(
                                "message",
                                ""
                        )
                );


            case "phone.alarm_set": {

                int hour =
                        payload.optInt(
                                "hour",
                                -1
                        );

                int minute =
                        payload.optInt(
                                "minute",
                                -1
                        );

                String reminderMessage =
                        payload.optString(
                                "message",
                                ""
                        ).trim();

                if (hour < 0 || hour > 23) {
                    throw new IllegalArgumentException(
                            "hour must be 0-23"
                    );
                }

                if (minute < 0 || minute > 59) {
                    throw new IllegalArgumentException(
                            "minute must be 0-59"
                    );
                }

                if (reminderMessage.isEmpty()) {
                    reminderMessage =
                            "JARVIS reminder";
                }

                Intent alarmIntent =
                        new Intent(
                                android.provider.AlarmClock
                                        .ACTION_SET_ALARM
                        );

                alarmIntent.putExtra(
                        android.provider.AlarmClock
                                .EXTRA_HOUR,
                        hour
                );

                alarmIntent.putExtra(
                        android.provider.AlarmClock
                                .EXTRA_MINUTES,
                        minute
                );

                alarmIntent.putExtra(
                        android.provider.AlarmClock
                                .EXTRA_MESSAGE,
                        reminderMessage
                );

                alarmIntent.putExtra(
                        android.provider.AlarmClock
                                .EXTRA_SKIP_UI,
                        true
                );

                alarmIntent.addFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK
                );

                if (
                        alarmIntent.resolveActivity(
                                getPackageManager()
                        ) == null
                ) {
                    throw new IllegalStateException(
                            "No alarm clock app available"
                    );
                }

                startActivity(alarmIntent);

                out.put("ok", true);
                out.put(
                        "provider",
                        "android_alarm_clock"
                );
                out.put(
                        "message",
                        reminderMessage
                );
                out.put("hour", hour);
                out.put("minute", minute);

                return out;
            }


            default:

                throw new IllegalArgumentException(
                        "Unsupported phone job: "
                                + jobType
                );
        }
    }


    private void handleCallerIntelligenceResult(
            JSONObject message
    ) {
        try {
            final String learnedName =
                    cleanCallValue(
                            message.optString(
                                    "display_name",
                                    ""
                            )
                    );

            final String learnedNumber =
                    cleanCallValue(
                            message.optString(
                                    "number",
                                    ""
                            )
                    );

            if (learnedName.isEmpty()
                    || learnedNumber.isEmpty()) {
                return;
            }

            callReactionHandler.post(() -> {

                // If there is no pending announcement, the call
                // already ended, was already announced, or the
                // phone is Silent/Vibrate.
                if (pendingCallAnnouncement == null) {
                    return;
                }

                if (!shouldSpeakIncomingCall()) {
                    return;
                }

                String currentNumber =
                        cleanCallValue(
                                pendingCallerNumber
                        );

                if (currentNumber.isEmpty()
                        || !sameIncomingPhoneNumber(
                                currentNumber,
                                learnedNumber
                        )) {
                    return;
                }

                // The pending announcement reads this field
                // when it actually speaks.
                pendingCallerName = learnedName;
            });

        } catch (Exception ignored) {
        }
    }


    private boolean sameIncomingPhoneNumber(
            String first,
            String second
    ) {
        String a = phoneDigitsOnly(first);
        String b = phoneDigitsOnly(second);

        if (a.isEmpty() || b.isEmpty()) {
            return false;
        }

        if (a.equals(b)) {
            return true;
        }

        int suffixLength =
                Math.min(
                        9,
                        Math.min(
                                a.length(),
                                b.length()
                        )
                );

        if (suffixLength < 7) {
            return false;
        }

        return a.substring(
                a.length() - suffixLength
        ).equals(
                b.substring(
                        b.length() - suffixLength
                )
        );
    }


    private String phoneDigitsOnly(String value) {
        if (value == null) {
            return "";
        }

        StringBuilder out =
                new StringBuilder();

        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);

            if (Character.isDigit(c)) {
                out.append(c);
            }
        }

        return out.toString();
    }


    private boolean containsHebrew(String value) {

        if (value == null || value.isBlank()) {
            return false;
        }

        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);

            if ((c >= '\u0590' && c <= '\u05FF')
                    || (c >= '\uFB1D' && c <= '\uFB4F')) {
                return true;
            }
        }

        return false;
    }


    private boolean shouldSpeakIncomingCall() {
        try {
            android.media.AudioManager audioManager =
                    (android.media.AudioManager)
                            getSystemService(AUDIO_SERVICE);

            if (audioManager == null) {
                return true;
            }

            return audioManager.getRingerMode()
                    == android.media.AudioManager.RINGER_MODE_NORMAL;

        } catch (Exception ignored) {
            return true;
        }
    }


    private void handleLiveCallReaction(Intent intent, boolean fromWhatsApp) {

        String state =
                cleanCallValue(
                        intent.getStringExtra("call_state")
                );

        if (!"ringing".equalsIgnoreCase(state)) {

            if ("idle".equalsIgnoreCase(state)
                    || "offhook".equalsIgnoreCase(state)) {

                if (pendingCallAnnouncement != null) {
                    callReactionHandler.removeCallbacks(
                            pendingCallAnnouncement
                    );
                    pendingCallAnnouncement = null;
                }

                pendingCallerName = "";
                pendingCallerNumber = "";

                // End of this call session. Allow the same caller to be
                // announced immediately if they start a new call.
                lastAnnouncedCallKey = "";
                lastAnnouncedCallAtMs = 0L;
            }

            return;
        }

        // Respect the phone's own sound mode.
        // Silent/Vibrate: do not speak locally.
        // The call event has already been sent to Oracle above.
        if (!shouldSpeakIncomingCall()) {
            if (pendingCallAnnouncement != null) {
                callReactionHandler.removeCallbacks(
                        pendingCallAnnouncement
                );
                pendingCallAnnouncement = null;
            }

            pendingCallerName = "";
            pendingCallerNumber = "";
            return;
        }

        String callerName =
                cleanCallValue(
                        intent.getStringExtra("caller_name")
                );

        String number =
                cleanCallValue(
                        intent.getStringExtra("call_number")
                );

        if (!callerName.isEmpty()) {
            pendingCallerName = callerName;
        }

        if (!number.isEmpty()) {
            pendingCallerNumber = number;
        }

        if (pendingCallAnnouncement != null) {
            callReactionHandler.removeCallbacks(
                    pendingCallAnnouncement
            );
        }

        pendingCallAnnouncement = () -> {
            pendingCallAnnouncement = null;

            String name = pendingCallerName;
            String phone = pendingCallerNumber;

            String key =
                    (!name.isEmpty() ? name : phone);

            if (key.isEmpty()) {
                key = "unknown";
            }

            long now =
                    System.currentTimeMillis();

            if (key.equals(lastAnnouncedCallKey)
                    && now - lastAnnouncedCallAtMs < 20000L) {
                return;
            }

            lastAnnouncedCallKey = key;
            lastAnnouncedCallAtMs = now;

            String speech;

            if (fromWhatsApp && !name.isEmpty()) {

                if (containsHebrew(name)) {
                    speech =
                            "?????, ???? ?????? ????? ?-" +
                            name +
                            ".";
                } else {
                    speech =
                            "Sir, " +
                            name +
                            " is calling you on WhatsApp.";
                }

            } else if (!name.isEmpty()) {

                if (containsHebrew(name)) {
                    speech =
                            "?????, " +
                            name +
                            " ????? ????.";
                } else {
                    speech =
                            "Sir, " +
                            name +
                            " is calling.";
                }

            } else if (!phone.isEmpty()) {
                speech =
                        "Sir, you have an incoming call from " +
                        speakablePhoneNumber(phone) +
                        ".";

            } else {
                speech =
                        "Sir, you have an incoming call.";
            }

            speakIncomingCall(speech);
        };

        long announcementDelayMs =
                pendingCallerName.isEmpty()
                        ? 1200L
                        : 650L;

        callReactionHandler.postDelayed(
                pendingCallAnnouncement,
                announcementDelayMs
        );
    }


    private String cleanCallValue(String value) {

        if (value == null) {
            return "";
        }

        String cleaned =
                value.trim();

        if ("null".equalsIgnoreCase(cleaned)
                || "unknown".equalsIgnoreCase(cleaned)) {
            return "";
        }

        return cleaned;
    }


    private String speakablePhoneNumber(String number) {

        if (number == null || number.isBlank()) {
            return "";
        }

        StringBuilder out =
                new StringBuilder();

        for (int i = 0; i < number.length(); i++) {

            char c =
                    number.charAt(i);

            if (Character.isDigit(c)) {

                if (out.length() > 0) {
                    out.append(' ');
                }

                out.append(c);
            }
        }

        return out.length() > 0
                ? out.toString()
                : number;
    }


    private synchronized void speakIncomingCall(
            String speech
    ) {

        if (speech == null || speech.isBlank()) {
            return;
        }

        pendingCallSpeech =
                speech;

        if (callTts != null && callTtsReady) {
            speakPendingCallNow();
            return;
        }

        if (callTts != null) {
            return;
        }

        callTts =
                new android.speech.tts.TextToSpeech(
                        getApplicationContext(),
                        status -> {

                            if (status
                                    != android.speech.tts.TextToSpeech.SUCCESS) {

                                callTtsReady = false;
                                return;
                            }

                            callTtsReady = true;

                            try {
                                callTts.setLanguage(
                                        java.util.Locale.getDefault()
                                );

                                callTts.setAudioAttributes(
                                        new android.media.AudioAttributes.Builder()
                                                .setUsage(
                                                        android.media.AudioAttributes
                                                                .USAGE_ASSISTANCE_NAVIGATION_GUIDANCE
                                                )
                                                .setContentType(
                                                        android.media.AudioAttributes
                                                                .CONTENT_TYPE_SPEECH
                                                )
                                                .build()
                                );

                            } catch (Exception ignored) {
                            }

                            speakPendingCallNow();
                        }
                );
    }


    private synchronized void speakPendingCallNow() {

        if (!callTtsReady
                || callTts == null
                || pendingCallSpeech == null
                || pendingCallSpeech.isBlank()) {
            return;
        }

        String speech =
                pendingCallSpeech;

        pendingCallSpeech =
                null;

        try {
            java.util.Locale speechLocale =
                    containsHebrew(speech)
                            ? new java.util.Locale("he", "IL")
                            : java.util.Locale.ENGLISH;

            int languageResult =
                    callTts.setLanguage(
                            speechLocale
                    );

            if (languageResult
                    == android.speech.tts.TextToSpeech.LANG_MISSING_DATA
                    || languageResult
                    == android.speech.tts.TextToSpeech.LANG_NOT_SUPPORTED) {

                // Do not change the phone UI language.
                // Fall back only for this spoken message.
                callTts.setLanguage(
                        java.util.Locale.getDefault()
                );
            }

            callTts.speak(
                    speech,
                    android.speech.tts.TextToSpeech.QUEUE_FLUSH,
                    null,
                    "jarvis-incoming-call"
            );
        } catch (Exception ignored) {
        }
    }


    private void sendPhoneStateEvent(Intent intent) {
        try {
            JSONObject payload = new JSONObject();

            payload.put("state",
                    intent.getStringExtra("call_state"));

            payload.put("direction",
                    intent.getStringExtra("call_direction"));

            payload.put("number",
                    intent.getStringExtra("call_number"));

            payload.put("caller_name",
                    intent.getStringExtra("caller_name"));

            payload.put(
                    "occurred_at_ms",
                    intent.getLongExtra(
                            "occurred_at_ms",
                            System.currentTimeMillis()
                    )
            );

            JSONObject event = new JSONObject();

            event.put("type", "device_event");
            event.put("event_type", "phone.call_state");

            event.put(
                    "event_id",
                    java.util.UUID.randomUUID()
                            .toString()
                            .replace("-", "")
            );

            event.put(
                    "occurred_at",
                    java.time.Instant.now().toString()
            );

            event.put("payload", payload);

            sendOrQueueDeviceEvent(event);

        } catch (Exception ignored) {
        }
    }


    private synchronized void sendOrQueueDeviceEvent(
            JSONObject event
    ) {

        if (event == null) return;

        WebSocket current = socket;

        if (current != null) {
            try {
                if (current.send(event.toString())) {
                    return;
                }
            } catch (Exception ignored) {
            }
        }

        try {
            String old =
                    getSharedPreferences(
                            PhoneApiClient.PREFS,
                            MODE_PRIVATE
                    )
                    .getString(
                            "phase2_pending_device_events",
                            "[]"
                    );

            org.json.JSONArray existing;

            try {
                existing =
                        new org.json.JSONArray(old);
            } catch (Exception ignored) {
                existing =
                        new org.json.JSONArray();
            }

            org.json.JSONArray compact =
                    new org.json.JSONArray();

            int start =
                    Math.max(
                            0,
                            existing.length() - 19
                    );

            for (
                    int i = start;
                    i < existing.length();
                    i++
            ) {
                compact.put(existing.opt(i));
            }

            compact.put(event);

            getSharedPreferences(
                    PhoneApiClient.PREFS,
                    MODE_PRIVATE
            )
                    .edit()
                    .putString(
                            "phase2_pending_device_events",
                            compact.toString()
                    )
                    .apply();

        } catch (Exception ignored) {
        }
    }


    private synchronized void flushQueuedDeviceEvents(
            WebSocket webSocket
    ) {

        if (webSocket == null) return;

        try {
            String old =
                    getSharedPreferences(
                            PhoneApiClient.PREFS,
                            MODE_PRIVATE
                    )
                    .getString(
                            "phase2_pending_device_events",
                            "[]"
                    );

            org.json.JSONArray existing =
                    new org.json.JSONArray(old);

            org.json.JSONArray remaining =
                    new org.json.JSONArray();

            for (
                    int i = 0;
                    i < existing.length();
                    i++
            ) {
                Object value =
                        existing.opt(i);

                if (!(value instanceof JSONObject)) {
                    continue;
                }

                boolean sent = false;

                try {
                    sent = webSocket.send(
                            value.toString()
                    );
                } catch (Exception ignored) {
                }

                if (!sent) {
                    remaining.put(value);
                }
            }

            getSharedPreferences(
                    PhoneApiClient.PREFS,
                    MODE_PRIVATE
            )
                    .edit()
                    .putString(
                            "phase2_pending_device_events",
                            remaining.toString()
                    )
                    .apply();

        } catch (Exception ignored) {
        }
    }


    private void markDisconnected() {

        getSharedPreferences(
                PhoneApiClient.PREFS,
                MODE_PRIVATE
        )
                .edit()
                .putBoolean(
                        "cloud_connected",
                        false
                )
                .apply();
    }

    private void reconnectLater() {

        if (!running) return;

        new Thread(() -> {

            try {
                Thread.sleep(5000);
            } catch (InterruptedException ignored) {
                Thread.currentThread().interrupt();
            }

            if (running) connect();

        }, "jarvis-cloud-reconnect").start();
    }

    @Override
    public void onDestroy() {


        callReactionHandler.removeCallbacksAndMessages(null);

        if (callTts != null) {
            try {
                callTts.stop();
                callTts.shutdown();
            } catch (Exception ignored) {
            }

            callTts = null;
            callTtsReady = false;
        }

        running = false;

        markDisconnected();

        if (socket != null) {
            socket.close(
                    1000,
                    "JARVIS service stopping"
            );
        }

        client.dispatcher().executorService().shutdown();

        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createChannel() {

        if (Build.VERSION.SDK_INT >= 26) {

            NotificationChannel channel =
                    new NotificationChannel(
                            CHANNEL,
                            "JARVIS Cloud",
                            NotificationManager.IMPORTANCE_LOW
                    );

            channel.setDescription(
                    "Keeps Samsung securely connected to JARVIS V30 Cloud."
            );

            getSystemService(
                    NotificationManager.class
            ).createNotificationChannel(channel);
        }
    }
}
