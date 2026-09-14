package com.jarvis.companion;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;

import org.json.JSONObject;

import java.net.InetAddress;
import java.net.URI;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeUnit;

import okhttp3.Dns;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

public final class PhoneApiClient {
    public static final String PREFS = "jarvis_companion";
    private static final MediaType JSON = MediaType.parse("application/json; charset=utf-8");
    private final Context context;

    public PhoneApiClient(Context context) {
        this.context = context.getApplicationContext();
    }

    public JSONObject pair(String serverUrl, String fallbackIp, String code) throws Exception {
        validateServerUrl(serverUrl);
        validateFallbackIp(fallbackIp, true);
        CryptoIdentity.ensureKey();
        JSONObject body = new JSONObject();
        body.put("code", code);
        body.put("device_name", Build.MANUFACTURER + " " + Build.MODEL);
        body.put("platform", "android");
        body.put("public_key", CryptoIdentity.publicKeyBase64());
        JSONObject response = post(serverUrl, fallbackIp, "/api/phone/pair", body.toString(), null, 12000, 12000);
        String deviceId = response.optString("device_id", "");
        if (deviceId.isEmpty()) throw new IllegalStateException("Pairing response did not contain a device id.");
        prefs().edit()
                .putString("server_url", trimSlash(serverUrl))
                .putString("tailscale_ipv4", fallbackIp == null ? "" : fallbackIp.trim())
                .putString("device_id", deviceId)
                .apply();
        return response;
    }

    public JSONObject health(String serverUrl, String fallbackIp) throws Exception {
        validateServerUrl(serverUrl);
        validateFallbackIp(fallbackIp, true);
        OkHttpClient client = clientFor(serverUrl, fallbackIp, 10000, 10000);
        Request request = new Request.Builder()
                .url(trimSlash(serverUrl) + "/api/phone/health")
                .header("Accept", "application/json")
                .get()
                .build();
        try (Response response = client.newCall(request).execute()) {
            String text = response.body() == null ? "" : response.body().string();
            if (!response.isSuccessful()) {
                if (response.code() == 502) throw new IllegalStateException("Reached Tailscale Serve, but the JARVIS phone bridge on the PC is not running (HTTP 502). Start JARVIS on the PC.");
                throw new IllegalStateException("Private JARVIS endpoint returned HTTP " + response.code() + ": " + text);
            }
            JSONObject out = text.isEmpty() ? new JSONObject() : new JSONObject(text);
            if (!out.optBoolean("ok", false)) throw new IllegalStateException("JARVIS endpoint answered, but health was not OK.");
            return out;
        }
    }

    public JSONObject signedPost(String path, JSONObject body, int readTimeoutMs) throws Exception {
        String server = prefs().getString("server_url", "");
        String fallbackIp = prefs().getString("tailscale_ipv4", "");
        String device = prefs().getString("device_id", "");
        if (server.isEmpty() || device.isEmpty()) throw new IllegalStateException("Phone is not paired.");
        validateServerUrl(server);
        validateFallbackIp(fallbackIp, true);
        String raw = body == null ? "{}" : body.toString();
        byte[] bytes = raw.getBytes(StandardCharsets.UTF_8);
        CryptoIdentity.SignedHeaders sig = CryptoIdentity.sign("POST", path, bytes);
        return post(server, fallbackIp, path, raw, new String[][] {
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
            throw new IllegalArgumentException("Use the HTTPS *.ts.net address shown by JARVIS. V29 keeps that hostname for TLS security.");
        }
    }

    public static void validateFallbackIp(String value, boolean allowBlank) {
        String ip = value == null ? "" : value.trim();
        if (ip.isEmpty() && allowBlank) return;
        String[] p = ip.split("\\.");
        if (p.length != 4) throw new IllegalArgumentException("Fallback IP must be the PC Tailscale IPv4 address (100.64.0.0/10). You may leave it blank if MagicDNS works.");
        try {
            int a = Integer.parseInt(p[0]);
            int b = Integer.parseInt(p[1]);
            int c = Integer.parseInt(p[2]);
            int d = Integer.parseInt(p[3]);
            if (a != 100 || b < 64 || b > 127 || c < 0 || c > 255 || d < 0 || d > 255) throw new IllegalArgumentException();
        } catch (Exception ex) {
            throw new IllegalArgumentException("Fallback IP must be the PC Tailscale IPv4 address (100.64.0.0/10). You may leave it blank if MagicDNS works.");
        }
    }

    private OkHttpClient clientFor(String server, String fallbackIp, int connectTimeout, int readTimeout) throws Exception {
        URI uri = new URI(server);
        final String jarvisHost = uri.getHost();
        final String ip = fallbackIp == null ? "" : fallbackIp.trim();

        Dns dns = hostname -> {
            if (!ip.isEmpty() && hostname.equalsIgnoreCase(jarvisHost)) {
                try {
                    // Numeric address: no MagicDNS lookup. The HTTPS request still uses
                    // jarvisHost, so TLS SNI and certificate verification stay correct.
                    return Collections.singletonList(InetAddress.getByName(ip));
                } catch (Exception ignored) {
                    // If the fallback is malformed/unavailable, use Android/Tailscale DNS.
                }
            }
            try {
                return Dns.SYSTEM.lookup(hostname);
            } catch (UnknownHostException ex) {
                throw ex;
            }
        };

        return new OkHttpClient.Builder()
                .dns(dns)
                .connectTimeout(connectTimeout, TimeUnit.MILLISECONDS)
                .readTimeout(readTimeout, TimeUnit.MILLISECONDS)
                .writeTimeout(readTimeout, TimeUnit.MILLISECONDS)
                .retryOnConnectionFailure(true)
                .build();
    }

    private static String trimSlash(String s) {
        String out = s.trim();
        while (out.endsWith("/")) out = out.substring(0, out.length() - 1);
        return out;
    }

    private JSONObject post(String server, String fallbackIp, String path, String body, String[][] headers, int connectTimeout, int readTimeout) throws Exception {
        OkHttpClient client = clientFor(server, fallbackIp, connectTimeout, readTimeout);
        RequestBody requestBody = RequestBody.create(body, JSON);
        Request.Builder builder = new Request.Builder()
                .url(trimSlash(server) + path)
                .header("Accept", "application/json")
                .post(requestBody);
        if (headers != null) for (String[] h : headers) builder.header(h[0], h[1]);

        try (Response response = client.newCall(builder.build()).execute()) {
            String text = response.body() == null ? "" : response.body().string();
            if (!response.isSuccessful()) throw new IllegalStateException("JARVIS server returned " + response.code() + ": " + text);
            return text.isEmpty() ? new JSONObject() : new JSONObject(text);
        }
    }
}
