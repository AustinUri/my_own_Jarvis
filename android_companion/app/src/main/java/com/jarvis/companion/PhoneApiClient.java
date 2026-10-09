package com.jarvis.companion;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;

import org.json.JSONObject;

import java.util.concurrent.TimeUnit;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

public final class PhoneApiClient {

    public static final String PREFS = "jarvis_companion";

    public static final String CLOUD =
            "https://uri-jarvis.duckdns.org";

    public static final String DEVICE_ID = "uri-s25";

    private static final MediaType JSON =
            MediaType.parse("application/json; charset=utf-8");

    private final Context context;

    private final OkHttpClient client =
            new OkHttpClient.Builder()
                    .connectTimeout(15, TimeUnit.SECONDS)
                    .readTimeout(180, TimeUnit.SECONDS)
                    .writeTimeout(30, TimeUnit.SECONDS)
                    .retryOnConnectionFailure(true)
                    .build();

    public PhoneApiClient(Context context) {
        this.context = context.getApplicationContext();
    }

    public JSONObject health() throws Exception {

        Request request = new Request.Builder()
                .url(CLOUD + "/api/v1/health")
                .get()
                .build();

        try (Response response = client.newCall(request).execute()) {

            String text = response.body() == null
                    ? ""
                    : response.body().string();

            if (!response.isSuccessful()) {
                throw new IllegalStateException(
                        "JARVIS Cloud returned HTTP " +
                        response.code()
                );
            }

            return new JSONObject(text);
        }
    }

    public JSONObject pair(String code) throws Exception {

        if (!code.matches("\\d{6}")) {
            throw new IllegalArgumentException(
                    "Enter the 6-digit pairing code."
            );
        }

        CryptoIdentity.ensureKey();

        JSONObject body = new JSONObject();

        body.put("code", code);
        body.put("device_id", DEVICE_ID);
        body.put(
                "device_name",
                Build.MANUFACTURER + " " + Build.MODEL
        );
        body.put("platform", "android");
        body.put(
                "public_key",
                CryptoIdentity.publicKeyBase64()
        );

        JSONObject response = post(
                "/api/v1/pairing/claim",
                body,
                null
        );

        String token =
                response.optString("device_token", "");

        if (token.isEmpty()) {
            throw new IllegalStateException(
                    "Cloud did not return a device credential."
            );
        }

        SecureTokenStore.save(context, token);

        prefs().edit()
                .putString("device_id", DEVICE_ID)
                .putBoolean("paired_v30", true)
                .apply();

        return response;
    }

    public String deviceToken() throws Exception {
        return SecureTokenStore.load(context);
    }

    public boolean isPaired() {
        return prefs().getBoolean("paired_v30", false);
    }

    public SharedPreferences prefs() {
        return context.getSharedPreferences(
                PREFS,
                Context.MODE_PRIVATE
        );
    }

    public JSONObject askJarvis(String text) throws Exception {
        String clean = text == null ? "" : text.trim();

        if (clean.isEmpty()) {
            throw new IllegalArgumentException("Enter a message for JARVIS.");
        }

        if (!isPaired()) {
            throw new IllegalStateException("Pair the Samsung with JARVIS Cloud first.");
        }

        JSONObject body = new JSONObject();
        body.put("text", clean);
        body.put("source_device", DEVICE_ID);
        body.put("memory_scope", "primary");
        body.put("use_memory", true);
        body.put("route", "auto");
        body.put("deep", false);
        body.put("temperature", 0.2);
        body.put("max_tokens", 500);

        return post(
                "/api/v1/device/" + DEVICE_ID + "/assistant/chat",
                body,
                deviceToken()
        );
    }

    private JSONObject post(
            String path,
            JSONObject body,
            String bearer
    ) throws Exception {

        RequestBody requestBody = RequestBody.create(
                body.toString(),
                JSON
        );

        Request.Builder builder =
                new Request.Builder()
                        .url(CLOUD + path)
                        .header("Accept", "application/json")
                        .post(requestBody);

        if (bearer != null && !bearer.isEmpty()) {
            builder.header(
                    "Authorization",
                    "Bearer " + bearer
            );
        }

        try (Response response =
                     client.newCall(builder.build()).execute()) {

            String text = response.body() == null
                    ? ""
                    : response.body().string();

            if (!response.isSuccessful()) {
                throw new IllegalStateException(
                        "JARVIS Cloud returned HTTP " +
                        response.code() +
                        ": " + text
                );
            }

            return text.isEmpty()
                    ? new JSONObject()
                    : new JSONObject(text);
        }
    }
}
