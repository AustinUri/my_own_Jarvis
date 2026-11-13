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
import android.os.Bundle;
import android.telecom.Call;
import android.telecom.CallAudioState;
import android.telecom.InCallService;
import android.util.Log;
import android.telecom.VideoProfile;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

public final class JarvisInCallService
        extends InCallService {

    private static final String LOG_TAG =
            "JARVIS_CALL";

    public static final class CallSnapshot {
        public final String displayName;
        public final String number;
        public final String role;
        public final Bitmap photo;
        public final boolean primary;

        CallSnapshot(
                String displayName,
                String number,
                String role,
                Bitmap photo,
                boolean primary
        ) {
            this.displayName =
                    displayName == null
                            ? ""
                            : displayName;
            this.number =
                    number == null
                            ? ""
                            : number;
            this.role =
                    role == null
                            ? ""
                            : role;
            this.photo = photo;
            this.primary = primary;
        }
    }

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

    private static volatile String operationMessage = "";
    private static volatile long operationMessageAt = 0L;

    private final Call.Callback callback =
            new Call.Callback() {

        @Override
        public void onStateChanged(
                Call call,
                int state
        ) {
            logTopology("state-changed:" + state);
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
            logTopology("conferenceable-changed");
            selectForegroundCall();
            refreshCurrentSnapshot();
            updateNotificationAndUi();
        }

        @Override
        public void onChildrenChanged(
                Call call,
                List<Call> children
        ) {
            logTopology("children-changed");
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

        @Override
        public void onConnectionEvent(
                Call call,
                String event,
                Bundle extras
        ) {
            String safeEvent =
                    event == null
                            ? ""
                            : event;

            Log.i(
                    LOG_TAG,
                    "connectionEvent=" + safeEvent
            );

            if (safeEvent.endsWith(
                    "CALL_MERGE_FAILED"
            )) {
                setOperationMessage(
                        "Merge failed — Telecom/carrier rejected it"
                );
            } else if (safeEvent.endsWith(
                    "CALL_HOLD_FAILED"
            )) {
                setOperationMessage(
                        "Hold failed — Telecom/carrier rejected it"
                );
            } else if (safeEvent.endsWith(
                    "CALL_SWITCH_FAILED"
            )) {
                setOperationMessage(
                        "Switch failed — Telecom/carrier rejected it"
                );
            } else if (safeEvent.endsWith(
                    "MERGE_COMPLETE"
            )) {
                setOperationMessage(
                        "Conference created"
                );
            }

            logTopology(
                    "connection-event"
            );

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

        logTopology("call-added");
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

        logTopology("call-removed");
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

        if (state == Call.STATE_HOLDING) {
            return true;
        }

        return state == Call.STATE_ACTIVE
                && call.getDetails().can(
                Call.Details.CAPABILITY_HOLD
        );
    }

    public static boolean toggleHoldCurrentCall() {
        Call call = currentCall;

        if (call == null
                || call.getDetails() == null) {
            setOperationMessage(
                    "Hold unavailable for this call"
            );
            return false;
        }

        int state = call.getState();

        if (state == Call.STATE_HOLDING) {
            setOperationMessage("Resuming call…");
            Log.i(LOG_TAG, "unhold requested");
            call.unhold();
            return true;
        }

        if (state == Call.STATE_ACTIVE
                && call.getDetails().can(
                Call.Details.CAPABILITY_HOLD
        )) {
            setOperationMessage("Putting call on hold…");
            Log.i(LOG_TAG, "hold requested");
            call.hold();
            return true;
        }

        setOperationMessage(
                "Hold unavailable for this call"
        );
        return false;
    }

    public static boolean canAddCallNow() {
        JarvisInCallService service = instance;

        if (service == null
                || currentCall == null) {
            return false;
        }

        int state = currentCall.getState();

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
        Call conference =
                findConferenceWithCapability(
                        Call.Details.CAPABILITY_SWAP_CONFERENCE
                );

        if (conference != null) {
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
        Call conference =
                findConferenceWithCapability(
                        Call.Details.CAPABILITY_SWAP_CONFERENCE
                );

        if (conference != null) {
            setOperationMessage("Switching conference calls…");
            Log.i(LOG_TAG, "swapConference requested");
            conference.swapConference();
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
            setOperationMessage(
                    "Switch unavailable — active + held calls not found"
            );
            return false;
        }

        // Do not manually hold() and immediately unhold() in the same
        // stack frame. Telecom owns foreground arbitration; unholding
        // the held call requests the platform to swap foreground calls.
        setOperationMessage("Switching calls…");
        Log.i(
                LOG_TAG,
                "swap separate calls: unhold held call"
        );
        held.unhold();
        return true;
    }

    public static boolean canMergeCalls() {
        Call[] pair = findConferenceablePair();

        if (pair != null) {
            return true;
        }

        return findConferenceWithCapability(
                Call.Details.CAPABILITY_MERGE_CONFERENCE
        ) != null;
    }

    public static boolean mergeCalls() {
        // IMPORTANT: two separate carrier calls are first merged through
        // Call.conference(other) when Telecom explicitly lists them as
        // conferenceable. CAPABILITY_MERGE_CONFERENCE is primarily for an
        // already-created Conference call whose children still need merging.
        Call[] pair = findConferenceablePair();

        if (pair != null) {
            setOperationMessage("Merging calls…");
            Log.i(
                    LOG_TAG,
                    "conference(pair) requested"
            );
            pair[0].conference(pair[1]);
            return true;
        }

        Call conference =
                findConferenceWithCapability(
                        Call.Details.CAPABILITY_MERGE_CONFERENCE
                );

        if (conference != null) {
            setOperationMessage("Merging conference…");
            Log.i(
                    LOG_TAG,
                    "mergeConference requested"
            );
            conference.mergeConference();
            return true;
        }

        setOperationMessage(
                "Merge unavailable — Telecom exposed no conferenceable pair"
        );
        logTopology("merge-unavailable");
        return false;
    }

    private static Call[] findConferenceablePair() {
        // Prefer the currently active call because that mirrors the normal
        // active + held GSM/IMS two-call flow.
        Call active =
                findCallInState(
                        Call.STATE_ACTIVE
                );

        Call[] activePair =
                conferenceablePairFor(active);

        if (activePair != null) {
            return activePair;
        }

        Call held =
                findCallInState(
                        Call.STATE_HOLDING
                );

        Call[] heldPair =
                conferenceablePairFor(held);

        if (heldPair != null) {
            return heldPair;
        }

        for (Call call : calls) {
            Call[] pair =
                    conferenceablePairFor(call);

            if (pair != null) {
                return pair;
            }
        }

        return null;
    }

    private static Call[] conferenceablePairFor(
            Call call
    ) {
        if (call == null
                || call.getState()
                == Call.STATE_DISCONNECTED) {
            return null;
        }

        List<Call> conferenceable =
                call.getConferenceableCalls();

        if (conferenceable == null
                || conferenceable.isEmpty()) {
            return null;
        }

        for (Call other : conferenceable) {
            if (other == null
                    || other == call
                    || other.getState()
                    == Call.STATE_DISCONNECTED) {
                continue;
            }

            return new Call[]{call, other};
        }

        return null;
    }

    private static Call findConferenceWithCapability(
            int capability
    ) {
        for (Call call : calls) {
            if (call == null
                    || call.getState()
                    == Call.STATE_DISCONNECTED
                    || call.getDetails() == null) {
                continue;
            }

            List<Call> children =
                    call.getChildren();

            boolean conference =
                    children != null
                            && !children.isEmpty();

            if (conference
                    && call.getDetails().can(
                    capability
            )) {
                return call;
            }
        }

        return null;
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

    public static List<CallSnapshot> visibleCallSnapshots() {
        ArrayList<CallSnapshot> out =
                new ArrayList<>();

        JarvisInCallService service = instance;

        if (service == null) {
            return out;
        }

        for (Call call : calls) {
            if (call == null
                    || call.getState()
                    == Call.STATE_DISCONNECTED
                    || call.getParent() != null) {
                continue;
            }

            List<Call> children =
                    call.getChildren();

            if (children != null
                    && !children.isEmpty()) {
                for (Call child : children) {
                    CallSnapshot snapshot =
                            service.snapshotForCall(
                                    child,
                                    "IN CONFERENCE",
                                    false
                            );

                    if (snapshot != null) {
                        out.add(snapshot);
                    }
                }

                continue;
            }

            CallSnapshot snapshot =
                    service.snapshotForCall(
                            call,
                            roleForState(
                                    call.getState()
                            ),
                            call == currentCall
                    );

            if (snapshot != null) {
                out.add(snapshot);
            }
        }

        // Some telephony implementations may momentarily expose children
        // without a visible parent in our current list. Do not leave the UI
        // blank in that transition.
        if (out.isEmpty()) {
            for (Call call : calls) {
                if (call == null
                        || call.getState()
                        == Call.STATE_DISCONNECTED) {
                    continue;
                }

                CallSnapshot snapshot =
                        service.snapshotForCall(
                                call,
                                roleForState(
                                        call.getState()
                                ),
                                call == currentCall
                        );

                if (snapshot != null) {
                    out.add(snapshot);
                }
            }
        }

        return out;
    }

    public static String lastOperationMessage() {
        String message = operationMessage;

        if (message == null
                || message.isEmpty()) {
            return "";
        }

        if (System.currentTimeMillis()
                - operationMessageAt
                > 8000L) {
            return "";
        }

        return message;
    }

    private static void setOperationMessage(
            String message
    ) {
        operationMessage =
                message == null
                        ? ""
                        : message;
        operationMessageAt =
                System.currentTimeMillis();
        broadcastUiUpdateStatic();
    }

    private CallSnapshot snapshotForCall(
            Call call,
            String role,
            boolean primary
    ) {
        if (call == null) {
            return null;
        }

        JarvisCallerIdentity.Result identity =
                JarvisCallerIdentity.resolve(
                        this,
                        numberFromCall(call),
                        telecomNameFromCall(call)
                );

        return new CallSnapshot(
                identity.displayName,
                identity.number,
                role,
                identity.photo,
                primary
        );
    }

    private static String roleForState(
            int state
    ) {
        switch (state) {
            case Call.STATE_ACTIVE:
                return "ACTIVE";

            case Call.STATE_HOLDING:
                return "ON HOLD";

            case Call.STATE_RINGING:
            case Call.STATE_SIMULATED_RINGING:
                return "RINGING";

            case Call.STATE_DIALING:
                return "CALLING";

            case Call.STATE_CONNECTING:
                return "CONNECTING";

            default:
                return "CALL";
        }
    }

    private static void logTopology(
            String reason
    ) {
        StringBuilder builder =
                new StringBuilder();

        builder.append(reason)
                .append(" calls=")
                .append(calls.size());

        int index = 0;

        for (Call call : calls) {
            if (call == null) {
                continue;
            }

            int capabilityMask = 0;

            if (call.getDetails() != null) {
                capabilityMask =
                        call.getDetails()
                                .getCallCapabilities();
            }

            List<Call> conf =
                    call.getConferenceableCalls();

            List<Call> children =
                    call.getChildren();

            builder.append(" | #")
                    .append(index++)
                    .append(" state=")
                    .append(call.getState())
                    .append(" caps=0x")
                    .append(Integer.toHexString(
                            capabilityMask
                    ))
                    .append(" conf=")
                    .append(
                            conf == null
                                    ? 0
                                    : conf.size()
                    )
                    .append(" children=")
                    .append(
                            children == null
                                    ? 0
                                    : children.size()
                    )
                    .append(" parent=")
                    .append(
                            call.getParent() != null
                    );
        }

        Log.i(
                LOG_TAG,
                builder.toString()
        );
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
