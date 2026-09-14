package com.jarvis.companion;

import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

public final class LocalVoiceRecorder {
    private static final int SAMPLE_RATE = 16000;
    private AudioRecord recorder;
    private Thread worker;
    private volatile boolean running;
    private final ByteArrayOutputStream pcm = new ByteArrayOutputStream();

    public synchronized void start() {
        if (running) return;
        pcm.reset();
        int min = AudioRecord.getMinBufferSize(SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
        int buffer = Math.max(4096, min * 2);
        recorder = new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, buffer);
        if (recorder.getState() != AudioRecord.STATE_INITIALIZED) {
            recorder.release(); recorder = null;
            throw new IllegalStateException("Android microphone recorder could not initialize.");
        }
        recorder.startRecording();
        running = true;
        worker = new Thread(() -> {
            byte[] data = new byte[buffer];
            long started = System.currentTimeMillis();
            while (running && System.currentTimeMillis() - started < 30000) {
                int n = recorder.read(data, 0, data.length);
                if (n > 0) synchronized (pcm) { pcm.write(data, 0, n); }
            }
            running = false;
        }, "jarvis-phone-mic");
        worker.start();
    }

    public synchronized byte[] stopToWav() throws Exception {
        if (!running && recorder == null) return new byte[0];
        running = false;
        try { if (recorder != null) recorder.stop(); } catch (Exception ignored) {}
        if (worker != null) worker.join(1500);
        if (recorder != null) { recorder.release(); recorder = null; }
        byte[] raw; synchronized (pcm) { raw = pcm.toByteArray(); }
        if (raw.length < 1600) return new byte[0];
        return wav(raw);
    }

    public boolean isRunning() { return running; }
    public boolean isActive() { return recorder != null; }

    private static byte[] wav(byte[] pcm) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream(pcm.length + 44);
        int dataLen = pcm.length;
        int byteRate = SAMPLE_RATE * 2;
        out.write("RIFF".getBytes("US-ASCII"));
        out.write(le32(36 + dataLen));
        out.write("WAVEfmt ".getBytes("US-ASCII"));
        out.write(le32(16));
        out.write(le16((short)1));
        out.write(le16((short)1));
        out.write(le32(SAMPLE_RATE));
        out.write(le32(byteRate));
        out.write(le16((short)2));
        out.write(le16((short)16));
        out.write("data".getBytes("US-ASCII"));
        out.write(le32(dataLen));
        out.write(pcm);
        return out.toByteArray();
    }
    private static byte[] le16(short v){return ByteBuffer.allocate(2).order(ByteOrder.LITTLE_ENDIAN).putShort(v).array();}
    private static byte[] le32(int v){return ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(v).array();}
}
