package city.retrobox.ds3diagnostic;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothDevice;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Log;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/** Experimental, foreground-only, one-shot PIN diagnostic for a specific DualShock 3. */
public class MainActivity extends Activity {
    private static final String TAG = "RetroBoxDS3";
    private static final String DS3 = "11:22:33:44:55:66";
    private static final String M3_HOST_MAC = "AA:BB:CC:DD:EE:FF";
    private static final int PERMISSION_REQUEST = 101;
    private static final long ARM_DURATION_MS = 60000L;
    private TextView output;
    private TextView status;
    private boolean registered;
    private boolean active;
    private String armedMode; // null, HOST_MAC, ASCII_0000
    private long expiresAt;

    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            String action = intent.getAction();
            BluetoothDevice device = intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE);
            if (device == null) return;
            String mac;
            try { mac = device.getAddress(); }
            catch (SecurityException e) { report("Permission denied reading device address: " + e); return; }
            if (!DS3.equalsIgnoreCase(mac)) return;
            if (BluetoothDevice.ACTION_PAIRING_REQUEST.equals(action)) {
                int variant = intent.getIntExtra(BluetoothDevice.EXTRA_PAIRING_VARIANT, -1);
                int key = intent.getIntExtra(BluetoothDevice.EXTRA_PAIRING_KEY, -1);
                report("PAIRING_REQUEST mac=" + mac + " variant=" + variant + " (" + variantName(variant) + ") pairingKeyPresent=" + (key != -1));
                if (armedMode == null) { report("DIAGNOSTIC_ONLY: no PIN submitted"); return; }
                if (!active || SystemClock.elapsedRealtime() >= expiresAt) {
                    disarm("Arm expired or app not foreground; no PIN sent");
                    return;
                }
                if (variant != BluetoothDevice.PAIRING_VARIANT_PIN) {
                    disarm("Unexpected pairing variant; no PIN sent");
                    return;
                }
                String mode = armedMode;
                // Consume exactly one permitted attempt, even if setPin throws or returns false.
                disarm("One-shot attempt consumed");
                byte[] pin = "HOST_MAC".equals(mode)
                    ? addressBytes(M3_HOST_MAC)
                    : "0000".getBytes(StandardCharsets.US_ASCII);
                report("PIN_ATTEMPT mode=" + mode + " pinHex=" + toHex(pin) + " length=" + pin.length);
                try {
                    boolean submitted = device.setPin(pin);
                    report("SET_PIN_RESULT=" + submitted + " (does NOT prove authentication success)");
                } catch (SecurityException e) {
                    report("SET_PIN_SECURITY_EXCEPTION=" + e);
                } catch (RuntimeException e) {
                    report("SET_PIN_ERROR=" + e);
                }
                // Do not abort/modify the ordered pairing broadcast; stock UI may also respond.
            } else if (BluetoothDevice.ACTION_BOND_STATE_CHANGED.equals(action)) {
                int state = intent.getIntExtra(BluetoothDevice.EXTRA_BOND_STATE, -1);
                int prior = intent.getIntExtra(BluetoothDevice.EXTRA_PREVIOUS_BOND_STATE, -1);
                report("BOND_STATE mac=" + mac + " " + bondName(prior) + " -> " + bondName(state));
                if (state == BluetoothDevice.BOND_BONDED) report("BONDED: check HID input separately via /proc/bus/input/devices");
            } else if (BluetoothDevice.ACTION_ACL_CONNECTED.equals(action)) {
                report("ACL_CONNECTED mac=" + mac);
            } else if (BluetoothDevice.ACTION_ACL_DISCONNECTED.equals(action)) {
                report("ACL_DISCONNECTED mac=" + mac);
            }
        }
    };

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(30, 20, 30, 20);
        TextView title = new TextView(this);
        title.setText("RetroBox DS3 Pairing Diagnostic v0.2");
        title.setTextSize(21);
        title.setGravity(Gravity.CENTER_VERTICAL);
        layout.addView(title);
        TextView info = new TextView(this);
        info.setText("Target DS3: " + DS3 + "\nM3 adapter: " + M3_HOST_MAC + "\nOne-shot manual test only; no PIN by default. Keep app visible.\n");
        info.setTextSize(15);
        layout.addView(info);
        status = new TextView(this);
        status.setTextSize(16);
        layout.addView(status);
        Button host = new Button(this);
        host.setText("ARM NEXT REQUEST: HOST MAC (6 raw bytes)");
        host.setOnClickListener(v -> arm("HOST_MAC"));
        layout.addView(host);
        Button ascii = new Button(this);
        ascii.setText("ARM NEXT REQUEST: ASCII 0000 (4 bytes)");
        ascii.setOnClickListener(v -> arm("ASCII_0000"));
        layout.addView(ascii);
        Button cancel = new Button(this);
        cancel.setText("DISARM / DIAGNOSTIC ONLY");
        cancel.setOnClickListener(v -> disarm("Manually disarmed"));
        layout.addView(cancel);
        ScrollView scroll = new ScrollView(this);
        output = new TextView(this);
        output.setTextSize(14);
        output.setTextIsSelectable(true);
        scroll.addView(output);
        layout.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(layout);
        updateStatus();
        report("Started; Android " + Build.VERSION.RELEASE + " (API " + Build.VERSION.SDK_INT + ")");
        if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
            report("Requesting BLUETOOTH_CONNECT permission. Please allow it.");
            requestPermissions(new String[] { Manifest.permission.BLUETOOTH_CONNECT }, PERMISSION_REQUEST);
        } else startListening();
    }

    @Override protected void onResume() { super.onResume(); active = true; }
    @Override protected void onPause() {
        active = false;
        disarm("App left foreground; disarmed for safety");
        super.onPause();
    }
    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == PERMISSION_REQUEST) {
            if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) startListening();
            else report("BLUETOOTH_CONNECT denied; cannot monitor.");
        }
    }
    private void startListening() {
        if (registered) return;
        IntentFilter filter = new IntentFilter();
        filter.addAction(BluetoothDevice.ACTION_PAIRING_REQUEST);
        filter.addAction(BluetoothDevice.ACTION_BOND_STATE_CHANGED);
        filter.addAction(BluetoothDevice.ACTION_ACL_CONNECTED);
        filter.addAction(BluetoothDevice.ACTION_ACL_DISCONNECTED);
        try {
            registerReceiver(receiver, filter);
            registered = true;
            report("Receiver registered; diagnostic only until ARM selected.");
        } catch (Exception e) { report("Receiver registration FAILED: " + e); }
    }
    private void arm(String mode) {
        if (!registered || checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
            report("Cannot arm: receiver/permission not ready"); return;
        }
        armedMode = mode;
        expiresAt = SystemClock.elapsedRealtime() + ARM_DURATION_MS;
        updateStatus();
        report("ARMED mode=" + mode + " for 60 sec / ONE matching PIN request. Press PS now.");
        status.postDelayed(() -> {
            if (armedMode != null && SystemClock.elapsedRealtime() >= expiresAt)
                disarm("60-second window expired");
        }, ARM_DURATION_MS + 100);
    }
    private void disarm(String reason) {
        if (armedMode != null) { armedMode = null; report("DISARMED: " + reason); }
        updateStatus();
    }
    private void updateStatus() {
        if (status != null) status.setText(armedMode == null ? "MODE: DIAGNOSTIC ONLY (safe)" : "MODE: ARMED " + armedMode + " — ONE REQUEST / 60s");
    }
    @Override protected void onDestroy() {
        if (registered) { unregisterReceiver(receiver); registered = false; }
        super.onDestroy();
    }
    private static byte[] addressBytes(String address) {
        String[] components = address.split(":");
        if (components.length != 6) throw new IllegalArgumentException("Invalid host Bluetooth address");
        byte[] bytes = new byte[6];
        for (int i = 0; i < 6; i++) bytes[i] = (byte) Integer.parseInt(components[i], 16);
        return bytes;
    }
    private static String toHex(byte[] data) {
        StringBuilder sb = new StringBuilder();
        for (byte b : data) sb.append(String.format(Locale.US, "%02X", b & 0xff));
        return sb.toString();
    }
    private static String variantName(int v) {
        switch (v) {
            case BluetoothDevice.PAIRING_VARIANT_PIN: return "PIN";
            case BluetoothDevice.PAIRING_VARIANT_PASSKEY_CONFIRMATION: return "PASSKEY_CONFIRMATION";
            default: return "UNKNOWN(" + v + ")";
        }
    }
    private static String bondName(int s) {
        switch (s) {
            case BluetoothDevice.BOND_NONE: return "NONE";
            case BluetoothDevice.BOND_BONDING: return "BONDING";
            case BluetoothDevice.BOND_BONDED: return "BONDED";
            default: return String.valueOf(s);
        }
    }
    private void report(String message) {
        String line = new SimpleDateFormat("HH:mm:ss.SSS", Locale.US).format(new Date()) + " " + message;
        Log.i(TAG, line);
        if (output != null) runOnUiThread(() -> output.append(line + "\n"));
    }
}
