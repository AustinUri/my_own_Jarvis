package com.jarvis.companion;

import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.Signature;
import java.security.spec.ECGenParameterSpec;
import java.util.Locale;
import java.util.UUID;

public final class CryptoIdentity {
    private static final String STORE = "AndroidKeyStore";
    private static final String ALIAS = "jarvis_companion_identity_v1";

    private CryptoIdentity() {}

    public static void ensureKey() throws Exception {
        KeyStore ks = KeyStore.getInstance(STORE);
        ks.load(null);
        if (ks.containsAlias(ALIAS)) return;
        KeyPairGenerator gen = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, STORE);
        KeyGenParameterSpec spec = new KeyGenParameterSpec.Builder(
                ALIAS, KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY)
                .setAlgorithmParameterSpec(new ECGenParameterSpec("secp256r1"))
                .setDigests(KeyProperties.DIGEST_SHA256)
                .setUserAuthenticationRequired(false)
                .build();
        gen.initialize(spec);
        gen.generateKeyPair();
    }

    public static String publicKeyBase64() throws Exception {
        ensureKey();
        KeyStore ks = KeyStore.getInstance(STORE);
        ks.load(null);
        PublicKey key = ks.getCertificate(ALIAS).getPublicKey();
        return Base64.encodeToString(key.getEncoded(), Base64.NO_WRAP);
    }

    public static SignedHeaders sign(String method, String path, byte[] body) throws Exception {
        ensureKey();
        String timestamp = Long.toString(System.currentTimeMillis() / 1000L);
        String nonce = UUID.randomUUID().toString();
        String digest = hex(MessageDigest.getInstance("SHA-256").digest(body));
        String canonical = method.toUpperCase(Locale.ROOT) + "\n" + path + "\n" + timestamp + "\n" + nonce + "\n" + digest;
        KeyStore ks = KeyStore.getInstance(STORE);
        ks.load(null);
        PrivateKey privateKey = (PrivateKey) ks.getKey(ALIAS, null);
        Signature signature = Signature.getInstance("SHA256withECDSA");
        signature.initSign(privateKey);
        signature.update(canonical.getBytes(StandardCharsets.UTF_8));
        String sig = Base64.encodeToString(signature.sign(), Base64.NO_WRAP);
        return new SignedHeaders(timestamp, nonce, sig);
    }

    private static String hex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) sb.append(String.format(Locale.ROOT, "%02x", b));
        return sb.toString();
    }

    public static final class SignedHeaders {
        public final String timestamp;
        public final String nonce;
        public final String signature;
        public SignedHeaders(String timestamp, String nonce, String signature) {
            this.timestamp = timestamp;
            this.nonce = nonce;
            this.signature = signature;
        }
    }
}
