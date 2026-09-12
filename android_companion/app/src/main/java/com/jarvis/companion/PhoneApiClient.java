package com.jarvis.companion;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URI;
import java.nio.charset.StandardCharsets;

public final class PhoneApiClient {
    public static final String PREFS = "jarvis_companion";
    private final Context context;

    public PhoneApiClient(Context context) {
        this.context = context.getApplicationContext();
    }

    public JSONObject pair(String serverUrl, String code) throws Exception {
        validateServerUrl(serverUrl);
        CryptoIdentity.ensureKey();
        JSONObject body = new JSONObject();
        body.put("code", code);
        body.put("device_name", Build.MANUFACTURER + " " + Build.MODEL);
        body.put("platform", "android");
        body.put("public_key", CryptoIdentity.publicKeyBase64());
        JSONObject response = post(serverUrl, "/api/phone/pair", body.toString(), null, 12000, 12000);
        String deviceId = response.optString("device_id", "");
        if (deviceId.isEmpty()) throw new IllegalStateException("Pairing response did not contain a device id.");
        prefs().edit().putString("server_url", trimSlash(serverUrl)).putString("device_id", deviceId).apply();
        return response;
    }

    public JSONObject signedPost(String path, JSONObject body, int readTimeoutMs) throws Exception {
        String server = prefs().getString("server_url", "");
        String device = prefs().getString("device_id", "");
        if (server.isEmpty() || device.isEmpty()) throw new IllegalStateException("Phone is not paired.");
        validateServerUrl(server);
        String raw = body == null ? "{}" : body.toString();
        byte[] bytes = raw.getBytes(StandardCharsets.UTF_8);
        CryptoIdentity.SignedHeaders sig = CryptoIdentity.sign("POST", path, bytes);
        return post(server, path, raw, new String[][] {
                {"X-Jarvis-Device", device},
                {"X-Jarvis-Time", sig.timestamp},
                {"X-Jarvis-Nonce", sig.nonce},
                {"X-Jarvis-Signature", sig.signature}
        }, 12000, readTimeoutMs);
    }

    public SharedPreferences prefs() {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public static void validateServerUrl(String value) {
        try {
            URI uri = new URI(value == null ? "" : value.trim());
            String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase();
            String host = uri.getHost() == null ? "" : uri.getHost().toLowerCase();
            int port = uri.getPort();
            String path = uri.getPath() == null ? "" : uri.getPath();
            if (!"https".equals(scheme) || !host.endsWith(".ts.net") || host.length() <= ".ts.net".length()
                    || uri.getUserInfo() != null || (port != -1 && port != 443) || (!path.isEmpty() && !"/".equals(path))) {
                throw new IllegalArgumentException();
            }
        } catch (Exception ex) {
            throw new IllegalArgumentException("Use only the HTTPS *.ts.net address shown by JARVIS. Public HTTP/LAN/custom-host addresses are refused.");
        }
    }

    private static String trimSlash(String s) {
        String out = s.trim();
        while (out.endsWith("/")) out = out.substring(0, out.length() - 1);
        return out;
    }

    private JSONObject post(String server, String path, String body, String[][] headers, int connectTimeout, int readTimeout) throws Exception {
        URL url = new URL(trimSlash(server) + path);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(connectTimeout);
        conn.setReadTimeout(readTimeout);
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        conn.setRequestProperty("Accept", "application/json");
        if (headers != null) for (String[] h : headers) conn.setRequestProperty(h[0], h[1]);
        byte[] data = body.getBytes(StandardCharsets.UTF_8);
        conn.setFixedLengthStreamingMode(data.length);
        try (OutputStream os = conn.getOutputStream()) { os.write(data); }
        int code = conn.getResponseCode();
        InputStream in = code >= 200 && code < 300 ? conn.getInputStream() : conn.getErrorStream();
        String text = readAll(in);
        if (code < 200 || code >= 300) throw new IllegalStateException("JARVIS server returned " + code + ": " + text);
        return text.isEmpty() ? new JSONObject() : new JSONObject(text);
    }

    private static String readAll(InputStream in) throws Exception {
        if (in == null) return "";
        StringBuilder sb = new StringBuilder();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) sb.append(line);
        }
        return sb.toString();
    }
}
