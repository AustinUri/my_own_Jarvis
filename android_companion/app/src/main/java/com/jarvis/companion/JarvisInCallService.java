package com.jarvis.companion;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Person;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.drawable.Icon;
import android.net.Uri;
import android.os.Build;
import android.telecom.Call;
import android.telecom.CallAudioState;
import android.telecom.InCallService;
import android.telecom.VideoProfile;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

public final class JarvisInCallService
        extends InCallService {

    public static final String ACTION_UI_UPDATE =
            "com.jarvis.companion.CALL_UI_UPDATE";

    public static final String ACTION_ANSWER =
            "com.jarvis.companion.CALL_ANSWER";

    public static final String ACTION_REJECT =
            "com.jarvis.companion.CALL_REJECT";

    public static final String ACTION_HANGUP =
            "com.jarvis.companion.CALL_HANGUP";

    private static final String CHANNEL_ID =
            "jarvis_calls_v4";

    private static final int NOTIFICATION_ID =
            2301;

    private static volatile JarvisInCallService instance;

    private static final CopyOnWriteArrayList<Call> calls =
            new CopyOnWriteArrayList<>();

    private static volatile Call currentCall;

    private static volatile JarvisCallerIdentity.Result
            currentIdentity =
            new JarvisCallerIdentity.Result(
                    "Unknown caller",
                    "",
                    null,
                    "number"
            );

    private static volatile boolean muted = false;
    private static volatile int audioRoute =
            CallAudioState.ROUTE_EARPIECE;
    private static volatile int supportedAudioRoutes = 0;
    private static volatile int routeBeforeSpeaker =
            CallAudioState.ROUTE_EARPIECE;

    private final Call.Callback callback =
            new Call.Callback() {

        @Override
        public void onStateChanged(
                Call call,
                int state
        ) {
            selectForegroundCall();
            refreshCurrentSnapshot();
            updateNotificationAndUi();
        }

        @Override
        public void onDetailsChanged(
                Call call,
                Call.Details details
        ) {
            selectForegroundCall();
            refreshCurrentSnapshot();
            updateNotificationAndUi();
        }

        @Override
        public void onConferenceableCallsChanged(
                Call call,
                List<Call> conferenceableCalls
        ) {
            selectForegroundCall();
            refreshCurrentSnapshot();
            updateNotificationAndUi();
        }

        @Override
        public void onChildrenChanged(
                Call call,
                List<Call> children
        ) {
            selectForegroundCall();
            refreshCurrentSnapshot();
            updateNotificationAndUi();
        }

        @Override
        public void onParentChanged(
                Call call,
                Call parent
        ) {
            selectForegroundCall();
            refreshCurrentSnapshot();
            updateNotificationAndUi();
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
    }

    @Override
    public void onDestroy() {
        instance = null;
        calls.clear();
        currentCall = null;
        cancelNotification();
        super.onDestroy();
    }

    @Override
    public void onCallAdded(Call call) {
        super.onCallAdded(call);

        if (call == null) {
            return;
        }

        if (!calls.contains(call)) {
            calls.add(call);
        }

        call.registerCallback(callback);

        selectForegroundCall();
        refreshCurrentSnapshot();
        updateNotificationAndUi();
    }

    @Override
    public void onCallRemoved(Call call) {
        if (call != null) {
            try {
                call.unregisterCallback(callback);
            } catch (Exception ignored) {
            }

            calls.remove(call);
        }

        selectForegroundCall();
        refreshCurrentSnapshot();

        if (calls.isEmpty()) {
            cancelNotification();
        } else {
            showCallNotification();
        }

        broadcastUiUpdate();

        super.onCallRemoved(call);
    }

    @Override
    public void onCallAudioStateChanged(
            CallAudioState audioState
    ) {
        super.onCallAudioStateChanged(audioState);

        if (audioState != null) {
            muted = audioState.isMuted();
            audioRoute = audioState.getRoute();
            supportedAudioRoutes =
                    audioState.getSupportedRouteMask();
        }

        broadcastUiUpdate();
    }

    public static boolean hasCurrentCall() {
        return currentCall != null;
    }

    public static int callCount() {
        int count = 0;

        for (Call call : calls) {
            if (call != null
                    && call.getState()
                    != Call.STATE_DISCONNECTED) {
                count++;
            }
        }

        return count;
    }

    public static int currentState() {
        Call call = currentCall;

        return call == null
                ? Call.STATE_DISCONNECTED
                : call.getState();
    }

    public static String currentDisplayName() {
        if (isCurrentConference()) {
            int participants =
                    currentConferenceParticipantCount();

            return participants > 0
                    ? "Conference call"
                    : "Conference";
        }

        JarvisCallerIdentity.Result identity =
                currentIdentity;

        return identity == null
                ? "Unknown caller"
                : identity.displayName;
    }

    public static String currentNumber() {
        if (isCurrentConference()) {
            int participants =
                    currentConferenceParticipantCount();

            return participants > 0
                    ? participants + " participants"
                    : "";
        }

        JarvisCallerIdentity.Result identity =
                currentIdentity;

        return identity == null
                ? ""
                : identity.number;
    }

    public static Bitmap currentPhoto() {
        if (isCurrentConference()) {
            return null;
        }

        JarvisCallerIdentity.Result identity =
                currentIdentity;

        return identity == null
                ? null
                : identity.photo;
    }

    public static String currentIdentitySource() {
        if (isCurrentConference()) {
            return "conference";
        }

        JarvisCallerIdentity.Result identity =
                currentIdentity;

        return identity == null
                ? ""
                : identity.source;
    }

    public static long currentConnectTimeMillis() {
        Call call = currentCall;

        if (call == null
                || call.getDetails() == null) {
            return 0L;
        }

        return call.getDetails()
                .getConnectTimeMillis();
    }

    public static boolean answerCurrentCall() {
        Call call = currentCall;

        if (call == null) {
            return false;
        }

        int state = call.getState();

        if (state != Call.STATE_RINGING
                && state != Call.STATE_SIMULATED_RINGING) {
            return false;
        }

        call.answer(
                VideoProfile.STATE_AUDIO_ONLY
        );

        return true;
    }

    public static boolean rejectCurrentCall() {
        Call call = currentCall;

        if (call == null) {
            return false;
        }

        int state = call.getState();

        if (state != Call.STATE_RINGING
                && state != Call.STATE_SIMULATED_RINGING) {
            return false;
        }

        if (Build.VERSION.SDK_INT
                >= Build.VERSION_CODES.R) {
            call.reject(
                    Call.REJECT_REASON_DECLINED
            );
        } else {
            call.reject(false, null);
        }

        return true;
    }

    public static boolean hangupCurrentCall() {
        Call call = currentCall;

        if (call == null) {
            return false;
        }

        int state = call.getState();

        if (state == Call.STATE_RINGING
                || state == Call.STATE_SIMULATED_RINGING
                || state == Call.STATE_DISCONNECTED) {
            return false;
        }

        call.disconnect();
        return true;
    }

    public static boolean isMuted() {
        return muted;
    }

    public static boolean toggleMute() {
        JarvisInCallService service =
                instance;

        if (service == null
                || currentCall == null) {
            return false;
        }

        boolean target =
                !muted;

        service.setMuted(target);

        // Optimistic UI update; platform callback will confirm.
        muted = target;
        broadcastUiUpdateStatic();

        return true;
    }

    public static boolean isSpeakerOn() {
        return audioRoute
                == CallAudioState.ROUTE_SPEAKER;
    }

    @SuppressWarnings("deprecation")
    public static boolean toggleSpeaker() {
        JarvisInCallService service =
                instance;

        if (service == null
                || currentCall == null) {
            return false;
        }

        if (isSpeakerOn()) {
            int target =
                    bestPrivateRoute();

            service.setAudioRoute(target);
            audioRoute = target;

        } else {
            routeBeforeSpeaker =
                    audioRoute;

            service.setAudioRoute(
                    CallAudioState.ROUTE_SPEAKER
            );

            audioRoute =
                    CallAudioState.ROUTE_SPEAKER;
        }

        broadcastUiUpdateStatic();

        return true;
    }

    public static boolean canHoldCurrentCall() {
        Call call = currentCall;

        if (call == null
                || call.getDetails() == null) {
            return false;
        }

        int state = call.getState();

        if (state != Call.STATE_ACTIVE
                && state != Call.STATE_HOLDING) {
            return false;
        }

        return state == Call.STATE_HOLDING
                || call.getDetails().can(
                Call.Details.CAPABILITY_HOLD
        )
                || call.getDetails().can(
                Call.Details.CAPABILITY_SUPPORT_HOLD
        );
    }

    public static boolean toggleHoldCurrentCall() {
        Call call = currentCall;

        if (call == null
                || call.getDetails() == null) {
            return false;
        }

        int state = call.getState();

        if (state == Call.STATE_HOLDING) {
            call.unhold();
            return true;
        }

        if (state == Call.STATE_ACTIVE
                && call.getDetails().can(
                Call.Details.CAPABILITY_HOLD
        )) {
            call.hold();
            return true;
        }

        return false;
    }

    public static boolean canAddCallNow() {
        JarvisInCallService service =
                instance;

        if (service == null
                || currentCall == null) {
            return false;
        }

        int state =
                currentCall.getState();

        if (state != Call.STATE_ACTIVE
                && state != Call.STATE_HOLDING) {
            return false;
        }

        try {
            return service.canAddCall();
        } catch (Exception ignored) {
            return false;
        }
    }

    public static boolean canSwapCalls() {
        Call call = currentCall;

        if (call != null
                && call.getDetails() != null
                && call.getDetails().can(
                Call.Details.CAPABILITY_SWAP_CONFERENCE
        )) {
            return true;
        }

        return findCallInState(
                Call.STATE_ACTIVE
        ) != null
                && findCallInState(
                Call.STATE_HOLDING
        ) != null;
    }

    public static boolean swapCalls() {
        Call call = currentCall;

        if (call != null
                && call.getDetails() != null
                && call.getDetails().can(
                Call.Details.CAPABILITY_SWAP_CONFERENCE
        )) {

            call.swapConference();
            return true;
        }

        Call active =
                findCallInState(
                        Call.STATE_ACTIVE
                );

        Call held =
                findCallInState(
                        Call.STATE_HOLDING
                );

        if (active == null
                || held == null
                || active == held) {
            return false;
        }

        if (active.getDetails() != null
                && active.getDetails().can(
                Call.Details.CAPABILITY_HOLD
        )) {
            active.hold();
        }

        held.unhold();

        return true;
    }

    public static boolean canMergeCalls() {
        for (Call call : calls) {
            if (call == null
                    || call.getState()
                    == Call.STATE_DISCONNECTED) {
                continue;
            }

            if (call.getDetails() != null
                    && call.getDetails().can(
                    Call.Details.CAPABILITY_MERGE_CONFERENCE
            )) {
                return true;
            }

            List<Call> conferenceable =
                    call.getConferenceableCalls();

            if (conferenceable != null
                    && !conferenceable.isEmpty()) {
                return true;
            }
        }

        return false;
    }

    public static boolean mergeCalls() {
        for (Call call : calls) {
            if (call == null
                    || call.getState()
                    == Call.STATE_DISCONNECTED) {
                continue;
            }

            if (call.getDetails() != null
                    && call.getDetails().can(
                    Call.Details.CAPABILITY_MERGE_CONFERENCE
            )) {

                call.mergeConference();
                return true;
            }

            List<Call> conferenceable =
                    call.getConferenceableCalls();

            if (conferenceable != null
                    && !conferenceable.isEmpty()) {

                Call other =
                        conferenceable.get(0);

                if (other != null
                        && other != call) {
                    call.conference(other);
                    return true;
                }
            }
        }

        return false;
    }

    public static boolean playDtmf(
            char digit
    ) {
        if (!(
                (digit >= '0' && digit <= '9')
                        || digit == '*'
                        || digit == '#'
        )) {
            return false;
        }

        Call call =
                findCallInState(
                        Call.STATE_ACTIVE
                );

        if (call == null) {
            call = currentCall;
        }

        if (call == null
                || call.getState()
                != Call.STATE_ACTIVE) {
            return false;
        }

        call.playDtmfTone(digit);
        return true;
    }

    public static void stopDtmf() {
        Call call =
                findCallInState(
                        Call.STATE_ACTIVE
                );

        if (call == null) {
            call = currentCall;
        }

        if (call != null) {
            call.stopDtmfTone();
        }
    }

    public static String currentStateLabel() {
        if (isCurrentConference()
                && currentState()
                == Call.STATE_ACTIVE) {
            return "Conference";
        }

        switch (currentState()) {
            case Call.STATE_RINGING:
            case Call.STATE_SIMULATED_RINGING:
                return "Incoming call";

            case Call.STATE_DIALING:
                return "Calling";

            case Call.STATE_CONNECTING:
                return "Connecting";

            case Call.STATE_ACTIVE:
                return callCount() > 1
                        ? "Connected \u2022 "
                        + callCount()
                        + " calls"
                        : "Connected";

            case Call.STATE_HOLDING:
                return "On hold";

            case Call.STATE_DISCONNECTED:
                return "Call ended";

            default:
                return "Call";
        }
    }

    private static int bestPrivateRoute() {
        int preferred =
                routeBeforeSpeaker;

        if (preferred != CallAudioState.ROUTE_SPEAKER
                && routeSupported(preferred)) {
            return preferred;
        }

        if (routeSupported(
                CallAudioState.ROUTE_BLUETOOTH
        )) {
            return CallAudioState.ROUTE_BLUETOOTH;
        }

        if (routeSupported(
                CallAudioState.ROUTE_WIRED_HEADSET
        )) {
            return CallAudioState.ROUTE_WIRED_HEADSET;
        }

        return CallAudioState.ROUTE_EARPIECE;
    }

    private static boolean routeSupported(
            int route
    ) {
        return supportedAudioRoutes == 0
                || (
                supportedAudioRoutes & route
        ) != 0;
    }

    private static Call findCallInState(
            int state
    ) {
        for (Call call : calls) {
            if (call != null
                    && call.getState()
                    == state) {
                return call;
            }
        }

        return null;
    }

    private static void selectForegroundCall() {
        Call best = null;
        int bestScore = -1;

        for (Call call : calls) {
            if (call == null) {
                continue;
            }

            int state = call.getState();

            if (state == Call.STATE_DISCONNECTED) {
                continue;
            }

            int score =
                    scoreForState(state);

            if (call.getChildren() != null
                    && !call.getChildren().isEmpty()) {
                score += 8;
            }

            if (score > bestScore) {
                best = call;
                bestScore = score;
            }
        }

        currentCall = best;
    }

    private static int scoreForState(
            int state
    ) {
        switch (state) {
            case Call.STATE_RINGING:
            case Call.STATE_SIMULATED_RINGING:
                return 100;

            case Call.STATE_DIALING:
                return 95;

            case Call.STATE_CONNECTING:
                return 92;

            case Call.STATE_ACTIVE:
                return 90;

            case Call.STATE_HOLDING:
                return 60;

            default:
                return 20;
        }
    }

    private static boolean isCurrentConference() {
        Call call = currentCall;

        return call != null
                && call.getChildren() != null
                && !call.getChildren().isEmpty();
    }

    private static int currentConferenceParticipantCount() {
        Call call = currentCall;

        if (call == null
                || call.getChildren() == null) {
            return 0;
        }

        return call.getChildren().size();
    }

    private void refreshCurrentSnapshot() {
        Call call = currentCall;

        if (call == null) {
            currentIdentity =
                    new JarvisCallerIdentity.Result(
                            "Unknown caller",
                            "",
                            null,
                            "number"
                    );
            return;
        }

        if (isCurrentConference()) {
            currentIdentity =
                    new JarvisCallerIdentity.Result(
                            "Conference call",
                            "",
                            null,
                            "conference"
                    );
            return;
        }

        String number =
                numberFromCall(call);

        String telecomName =
                telecomNameFromCall(call);

        currentIdentity =
                JarvisCallerIdentity.resolve(
                        this,
                        number,
                        telecomName
                );
    }

    private String numberFromCall(Call call) {
        if (call == null
                || call.getDetails() == null) {
            return "";
        }

        Uri handle =
                call.getDetails().getHandle();

        if (handle == null) {
            return "";
        }

        String number =
                handle.getSchemeSpecificPart();

        return number == null
                ? ""
                : number.trim();
    }

    private String telecomNameFromCall(
            Call call
    ) {
        if (call == null
                || call.getDetails() == null) {
            return "";
        }

        CharSequence name =
                call.getDetails()
                        .getCallerDisplayName();

        return name == null
                ? ""
                : name.toString().trim();
    }

    private void updateNotificationAndUi() {
        if (currentCall == null) {
            cancelNotification();
        } else {
            showCallNotification();
        }

        broadcastUiUpdate();
    }

    private void showCallNotification() {
        if (currentCall == null) {
            return;
        }

        ensureNotificationChannel();

        PendingIntent contentIntent =
                callUiPendingIntent(
                        "OPEN",
                        2301
                );

        PendingIntent answerIntent =
                callUiPendingIntent(
                        ACTION_ANSWER,
                        2302
                );

        PendingIntent rejectIntent =
                callUiPendingIntent(
                        ACTION_REJECT,
                        2303
                );

        PendingIntent hangupIntent =
                callUiPendingIntent(
                        ACTION_HANGUP,
                        2304
                );

        Notification.Builder builder =
                Build.VERSION.SDK_INT
                        >= Build.VERSION_CODES.O
                        ? new Notification.Builder(
                                this,
                                CHANNEL_ID
                        )
                        : new Notification.Builder(
                                this
                        );

        String displayName =
                currentDisplayName();

        Bitmap photo =
                currentPhoto();

        builder
                .setSmallIcon(
                        android.R.drawable
                                .sym_call_incoming
                )
                .setCategory(
                        Notification.CATEGORY_CALL
                )
                .setOngoing(true)
                .setAutoCancel(false)
                .setContentTitle(displayName)
                .setContentText(
                        currentStateLabel()
                )
                .setContentIntent(contentIntent)
                .setFullScreenIntent(
                        contentIntent,
                        true
                )
                .setPriority(
                        Notification.PRIORITY_MAX
                )
                .setVisibility(
                        Notification.VISIBILITY_PUBLIC
                );

        if (photo != null) {
            builder.setLargeIcon(photo);
        }

        int state =
                currentState();

        if (Build.VERSION.SDK_INT
                >= Build.VERSION_CODES.S) {

            Person.Builder personBuilder =
                    new Person.Builder()
                            .setName(displayName)
                            .setImportant(true);

            if (photo != null) {
                personBuilder.setIcon(
                        Icon.createWithBitmap(photo)
                );
            }

            Person caller =
                    personBuilder.build();

            if (state == Call.STATE_RINGING
                    || state
                    == Call.STATE_SIMULATED_RINGING) {

                builder.setStyle(
                        Notification.CallStyle
                                .forIncomingCall(
                                        caller,
                                        rejectIntent,
                                        answerIntent
                                )
                );

            } else {

                builder.setStyle(
                        Notification.CallStyle
                                .forOngoingCall(
                                        caller,
                                        hangupIntent
                                )
                );
            }

        } else {

            if (state == Call.STATE_RINGING
                    || state
                    == Call.STATE_SIMULATED_RINGING) {

                builder.addAction(
                        android.R.drawable
                                .sym_call_outgoing,
                        "Answer",
                        answerIntent
                );

                builder.addAction(
                        android.R.drawable
                                .sym_call_missed,
                        "Reject",
                        rejectIntent
                );

            } else {

                builder.addAction(
                        android.R.drawable
                                .sym_call_missed,
                        "Hang up",
                        hangupIntent
                );
            }
        }

        NotificationManager manager =
                getSystemService(
                        NotificationManager.class
                );

        if (manager != null) {
            manager.notify(
                    NOTIFICATION_ID,
                    builder.build()
            );
        }
    }

    private PendingIntent callUiPendingIntent(
            String action,
            int requestCode
    ) {
        Intent intent =
                new Intent(
                        this,
                        JarvisCallActivity.class
                );

        intent.setAction(action);

        intent.addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_SINGLE_TOP
                        | Intent.FLAG_ACTIVITY_CLEAR_TOP
        );

        return PendingIntent.getActivity(
                this,
                requestCode,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT
                        | PendingIntent.FLAG_IMMUTABLE
        );
    }

    private void ensureNotificationChannel() {
        if (Build.VERSION.SDK_INT
                < Build.VERSION_CODES.O) {
            return;
        }

        NotificationManager manager =
                getSystemService(
                        NotificationManager.class
                );

        if (manager == null) {
            return;
        }

        NotificationChannel channel =
                new NotificationChannel(
                        CHANNEL_ID,
                        "JARVIS calls",
                        NotificationManager
                                .IMPORTANCE_HIGH
                );

        channel.setDescription(
                "Incoming and ongoing calls handled by JARVIS"
        );

        channel.setLockscreenVisibility(
                Notification.VISIBILITY_PUBLIC
        );

        manager.createNotificationChannel(
                channel
        );
    }

    private void cancelNotification() {
        NotificationManager manager =
                getSystemService(
                        NotificationManager.class
                );

        if (manager != null) {
            manager.cancel(
                    NOTIFICATION_ID
            );
        }
    }

    private void broadcastUiUpdate() {
        Intent intent =
                new Intent(ACTION_UI_UPDATE);

        intent.setPackage(
                getPackageName()
        );

        sendBroadcast(intent);
    }

    private static void broadcastUiUpdateStatic() {
        JarvisInCallService service =
                instance;

        if (service != null) {
            service.broadcastUiUpdate();
        }
    }
}
