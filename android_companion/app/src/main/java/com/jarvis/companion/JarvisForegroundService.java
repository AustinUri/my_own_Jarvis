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

    public static final String CHANNEL =
            "jarvis_cloud_link";

    private static final int NOTIFICATION_ID = 3001;

    private volatile boolean running;

    private WebSocket socket;

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
                                "Connected to JARVIS Cloud"
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
