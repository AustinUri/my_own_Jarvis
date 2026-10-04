package com.jarvis.companion;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

public final class SecureTokenStore {
    private static final String STORE = "AndroidKeyStore";
    private static final String ALIAS = "jarvis_cloud_token_key_v30";
    private static final String PREFS = "jarvis_companion";
    private static final String TOKEN = "cloud_device_token";
    private static final String IV = "cloud_device_token_iv";

    private SecureTokenStore() {}

    private static SecretKey getOrCreateKey() throws Exception {
        KeyStore ks = KeyStore.getInstance(STORE);
        ks.load(null);

        if (ks.containsAlias(ALIAS)) {
            return (SecretKey) ks.getKey(ALIAS, null);
        }

        KeyGenerator generator = KeyGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_AES,
                STORE
        );

        generator.init(new KeyGenParameterSpec.Builder(
                ALIAS,
                KeyProperties.PURPOSE_ENCRYPT |
                KeyProperties.PURPOSE_DECRYPT
        )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .build());

        return generator.generateKey();
    }

    public static void save(Context context, String token) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey());

        byte[] encrypted = cipher.doFinal(
                token.getBytes(StandardCharsets.UTF_8)
        );

        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString(TOKEN, Base64.encodeToString(encrypted, Base64.NO_WRAP))
                .putString(IV, Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP))
                .apply();
    }

    public static String load(Context context) throws Exception {
        String enc = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .getString(TOKEN, "");

        String iv = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .getString(IV, "");

        if (enc.isEmpty() || iv.isEmpty()) return "";

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");

        cipher.init(
                Cipher.DECRYPT_MODE,
                getOrCreateKey(),
                new GCMParameterSpec(
                        128,
                        Base64.decode(iv, Base64.NO_WRAP)
                )
        );

        byte[] plain = cipher.doFinal(
                Base64.decode(enc, Base64.NO_WRAP)
        );

        return new String(plain, StandardCharsets.UTF_8);
    }

    public static void clear(Context context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .remove(TOKEN)
                .remove(IV)
                .apply();
    }
}
