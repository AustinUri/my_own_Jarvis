package com.jarvis.companion;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;

import org.json.JSONObject;

public final class WhatsAppBridge {
    private WhatsAppBridge() {}

    public static JSONObject compose(Context context, String rawNumber, String name, String message) throws Exception {
        String text = message == null ? "" : message.trim();
        if (text.isEmpty()) throw new IllegalArgumentException("WhatsApp message is empty.");

        String canonical = PhoneNumbers.canonical(rawNumber);
        if (canonical.isEmpty()) throw new IllegalArgumentException("Contact has no usable phone number.");
        String digits = canonical.replaceAll("[^0-9]", "");
        if (digits.isEmpty()) throw new IllegalArgumentException("Contact has no usable WhatsApp number.");

        Uri uri = Uri.parse("https://wa.me/" + digits + "?text=" + Uri.encode(text));
        Intent intent = new Intent(Intent.ACTION_VIEW, uri);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        // Prefer the normal WhatsApp app, then WhatsApp Business. If neither is
        // installed Android can still resolve the wa.me URL in a browser.
        PackageManager pm = context.getPackageManager();
        String targetPackage = null;
        try { pm.getPackageInfo("com.whatsapp", 0); targetPackage = "com.whatsapp"; }
        catch (Exception ignored) {
            try { pm.getPackageInfo("com.whatsapp.w4b", 0); targetPackage = "com.whatsapp.w4b"; }
            catch (Exception ignored2) {}
        }
        if (targetPackage != null) intent.setPackage(targetPackage);

        // Android can restrict activity launches initiated by a background foreground
        // service. Try the direct open for the normal interactive case, and also create
        // an auto-cancel notification whose PendingIntent is a reliable user-gesture
        // continuation if Android keeps WhatsApp in the background.
        boolean directOpenAttempted = false;
        try {
            context.startActivity(intent);
            directOpenAttempted = true;
        } catch (Exception ignored) {}
        postReadyNotification(context, intent, name, text);

        JSONObject out = new JSONObject();
        out.put("ok", true);
        out.put("mode", "whatsapp-compose");
        out.put("name", name == null ? "" : name);
        out.put("number", PhoneNumbers.displayIsraelLocal(rawNumber));
        out.put("canonical_number", canonical);
        out.put("message_text", text);
        out.put("requires_user_send", true);
        out.put("direct_open_attempted", directOpenAttempted);
        out.put("message", "WhatsApp message prepared. If WhatsApp did not open automatically, tap the JARVIS notification; then review and tap Send.");
        return out;
    }

    private static void postReadyNotification(Context context, Intent intent, String name, String text) {
        try {
            final String channelId = "jarvis_whatsapp_ready";
            NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm == null) return;
            if (Build.VERSION.SDK_INT >= 26) {
                NotificationChannel ch = new NotificationChannel(channelId, "JARVIS WhatsApp actions", NotificationManager.IMPORTANCE_HIGH);
                ch.setDescription("Tap to review WhatsApp messages prepared by JARVIS.");
                nm.createNotificationChannel(ch);
            }
            PendingIntent pi = PendingIntent.getActivity(
                    context,
                    (int)(System.currentTimeMillis() & 0x7fffffff),
                    intent,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            String who = (name == null || name.trim().isEmpty()) ? "contact" : name.trim();
            String preview = text.length() > 90 ? text.substring(0, 90) + "…" : text;
            Notification n = new Notification.Builder(context, channelId)
                    .setContentTitle("WhatsApp message ready for " + who)
                    .setContentText(preview)
                    .setSmallIcon(android.R.drawable.sym_action_chat)
                    .setContentIntent(pi)
                    .setAutoCancel(true)
                    .build();
            nm.notify(2920, n);
        } catch (Exception ignored) {}
    }
}
