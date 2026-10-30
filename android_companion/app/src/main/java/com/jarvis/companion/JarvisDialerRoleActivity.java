package com.jarvis.companion;

import android.app.Activity;
import android.app.role.RoleManager;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class JarvisDialerRoleActivity extends Activity {
    private static final int REQUEST_DIALER_ROLE = 2303;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(48, 64, 48, 64);

        TextView warning = new TextView(this);
        warning.setText("Developer test only.\n\nDo not make JARVIS the default Phone app until Phase 2.3A has been built and tested.");
        warning.setTextSize(18f);

        Button request = new Button(this);
        request.setText("Request default Phone role");
        request.setOnClickListener(v -> requestDialerRole());

        root.addView(warning);
        root.addView(request);
        setContentView(root);
    }

    private void requestDialerRole() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            Toast.makeText(this, "ROLE_DIALER requires Android 10+ in this test flow", Toast.LENGTH_LONG).show();
            return;
        }
        RoleManager roleManager = getSystemService(RoleManager.class);
        if (roleManager == null || !roleManager.isRoleAvailable(RoleManager.ROLE_DIALER)) {
            Toast.makeText(this, "Dialer role unavailable", Toast.LENGTH_LONG).show();
            return;
        }
        if (roleManager.isRoleHeld(RoleManager.ROLE_DIALER)) {
            Toast.makeText(this, "JARVIS is already the default Phone app", Toast.LENGTH_LONG).show();
            return;
        }
        Intent intent = roleManager.createRequestRoleIntent(RoleManager.ROLE_DIALER);
        startActivityForResult(intent, REQUEST_DIALER_ROLE);
    }
}
