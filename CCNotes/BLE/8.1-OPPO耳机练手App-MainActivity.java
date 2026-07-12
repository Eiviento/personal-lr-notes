package com.example.blelab;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.bluetooth.*;
import android.bluetooth.le.*;
import android.content.pm.PackageManager;
import android.os.*;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.*;
import java.util.*;

/**
 * BLE 练手 App — OPPO Enco Air2
 *
 * ====== 协议操作流程 ======
 *
 *   扫描    → LL: Standby→Scanning, Advertising Report
 *   连接    → LL: Standby→Initiating, CONNECT_IND → Connection
 *   MTU协商 → ATT: EXCHANGE_MTU_REQ/RSP
 *   服务发现 → ATT: READ_BY_GROUP_TYPE → READ_BY_TYPE → FIND_INFO
 *   读特征值 → ATT: READ_REQ → READ_RSP
 *   写特征值 → ATT: WRITE_REQ → WRITE_RSP / WRITE_CMD
 *   订阅通知 → ATT: WRITE_REQ(CCCD=0x0001), HANDLE_VALUE_NOTIFICATION
 *   断开    → LL: LL_TERMINATE_IND
 *
 * ====== 关键验证点 ======
 *
 *   ① requestMtu() 必须在 discoverServices() 之前调用
 *   ② setCharacteristicNotification() + writeDescriptor(CCCD) 两步缺一不可
 *   ③ 重连后 CCCD 自动归零 → 必须重新写 CCCD
 *   ④ 所有 BLE 操作异步回调，不可在主线程阻塞等待
 *   ⑤ Android 10- 需要定位权限才能扫描 BLE
 */
public class MainActivity extends Activity {

    private static final String TAG = "BLE_LAB";

    // ==================== OPPO Enco Air2 UUID（nRF Connect 侦察结果） ====================

    // 标准 Service
    private static final UUID SRV_GENERIC_ACCESS    = UUID.fromString("00001800-0000-1000-8000-00805f9b34fb");
    private static final UUID SRV_DEVICE_INFO       = UUID.fromString("0000180a-0000-1000-8000-00805f9b34fb");

    // 标准 Characteristic（Device Information Service）
    private static final UUID CHAR_MODEL_NUMBER     = UUID.fromString("00002a24-0000-1000-8000-00805f9b34fb");
    private static final UUID CHAR_FIRMWARE_REV     = UUID.fromString("00002a28-0000-1000-8000-00805f9b34fb");
    private static final UUID CHAR_MANUFACTURER     = UUID.fromString("00002a29-0000-1000-8000-00805f9b34fb");

    // 厂商自定义 Service 1: 0000FF00
    private static final UUID SRV_FF00              = UUID.fromString("0000ff00-0000-1000-8000-00805f9b34fb");
    private static final UUID CHAR_FF01             = UUID.fromString("0000ff01-0000-1000-8000-00805f9b34fb"); // NOTIFY
    private static final UUID CHAR_FF02             = UUID.fromString("0000ff02-0000-1000-8000-00805f9b34fb"); // WRITE, WRITE_NO_RESPONSE
    private static final UUID CHAR_FF03             = UUID.fromString("0000ff03-0000-1000-8000-00805f9b34fb"); // WRITE, WRITE_NO_RESPONSE

    // 厂商自定义 Service 2: 00001234
    private static final UUID SRV_1234              = UUID.fromString("00001234-0000-1000-8000-00805f9b34fb");
    private static final UUID CHAR_1235             = UUID.fromString("00001235-0000-1000-8000-00805f9b34fb"); // READ, WRITE
    private static final UUID CHAR_1236             = UUID.fromString("00001236-0000-1000-8000-00805f9b34fb"); // NOTIFY, INDICATE

    // CCCD 标准 UUID
    private static final UUID CCCD                  = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");

    // ==================== 状态变量 ====================

    private BluetoothAdapter    bluetoothAdapter;
    private BluetoothLeScanner  leScanner;
    private BluetoothGatt       bluetoothGatt;
    private boolean             isScanning = false;

    // 标记是否已订阅通知（用于重连时验证 CCCD 丢失）
    private boolean             isSubscribed = false;

    // 日志缓冲区
    private final StringBuilder logBuilder   = new StringBuilder();

    // ==================== UI ====================

    private TextView  tvStatus;
    private TextView  tvLog;
    private Button    btnScan;
    private Button    btnReadInfo;
    private Button    btnRead1235;
    private Button    btnWriteFF02;
    private Button    btnSubscribe;
    private Button    btnDisconnect;
    private ScrollView scrollLog;

    // ==================== 权限 ====================

    private static final int REQ_PERM = 1;

    // ==================== 生命周期 ====================

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUI();         // 动态构建 UI，省去 XML
        initBluetooth();
        checkPermissions();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        closeGatt();
    }

    // ==================== UI 构建（动态，无 XML 依赖） ====================

    @SuppressLint("SetTextI18n")
    private void buildUI() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(40, 60, 40, 40);

        // 标题
        TextView title = new TextView(this);
        title.setText("🔬 BLE 练手 — OPPO Enco Air2");
        title.setTextSize(20);
        title.setPadding(0, 0, 0, 8);
        root.addView(title);

        // 状态
        tvStatus = new TextView(this);
        tvStatus.setText("状态：初始化中...");
        tvStatus.setTextSize(14);
        tvStatus.setPadding(0, 0, 0, 12);
        root.addView(tvStatus);

        // 按钮行
        root.addView(makeButtonRow(
            btnScan       = btn("🔍 扫描连接"),
            btnReadInfo   = btn("📋 读设备信息")
        ));
        root.addView(makeButtonRow(
            btnRead1235   = btn("📖 读1235"),
            btnWriteFF02  = btn("✏️ 写FF02")
        ));
        root.addView(makeButtonRow(
            btnSubscribe  = btn("🔔 订阅1236"),
            btnDisconnect = btn("❌ 断开")
        ));

        // 初始禁用操作按钮
        setButtonsEnabled(false);

        // 日志区
        TextView logLabel = new TextView(this);
        logLabel.setText("── 协议日志 ──");
        logLabel.setTextSize(13);
        logLabel.setPadding(0, 16, 0, 4);
        root.addView(logLabel);

        tvLog = new TextView(this);
        tvLog.setTextSize(12);
        tvLog.setBackgroundColor(0xFF1E1E1E);
        tvLog.setTextColor(0xFF00FF00);
        tvLog.setPadding(16, 12, 16, 12);
        tvLog.setHorizontallyScrolling(true);

        scrollLog = new ScrollView(this);
        scrollLog.addView(tvLog);
        scrollLog.setLayoutParams(new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
        root.addView(scrollLog);

        setContentView(root);
    }

    private LinearLayout makeButtonRow(Button b1, Button b2) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, 4, 0, 4);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, 120, 1);
        lp.setMargins(0, 0, 8, 0);
        row.addView(b1, lp);
        LinearLayout.LayoutParams lp2 = new LinearLayout.LayoutParams(0, 120, 1);
        row.addView(b2, lp2);
        return row;
    }

    private Button btn(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextSize(13);
        b.setAllCaps(false);
        b.setGravity(Gravity.CENTER);
        return b;
    }

    // ==================== BLE 初始化 ====================

    private void initBluetooth() {
        BluetoothManager mgr = (BluetoothManager) getSystemService(BLUETOOTH_SERVICE);
        if (mgr == null) {
            log("❌ 设备不支持蓝牙");
            return;
        }
        bluetoothAdapter = mgr.getAdapter();
        if (bluetoothAdapter == null || !bluetoothAdapter.isEnabled()) {
            log("⚠️ 请先打开手机蓝牙");
            tvStatus.setText("状态：蓝牙未开启");
            return;
        }
        leScanner = bluetoothAdapter.getBluetoothLeScanner();
        log("✅ 蓝牙已就绪，适配器: " + bluetoothAdapter.getName());
        tvStatus.setText("状态：蓝牙就绪");
    }

    private void checkPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            // Android 12+
            if (checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) != PackageManager.PERMISSION_GRANTED
             || checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{
                    Manifest.permission.BLUETOOTH_SCAN,
                    Manifest.permission.BLUETOOTH_CONNECT
                }, REQ_PERM);
            }
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            // Android 6-11: BLE 扫描需要定位权限 ← 这就是"开 GPS 才能扫 BLE"的根源
            if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{
                    Manifest.permission.ACCESS_FINE_LOCATION
                }, REQ_PERM);
            }
        }
    }

    /** 运行时权限检查工具方法，在启动扫描/连接前调用 */
    private boolean hasBlePermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            return checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) == PackageManager.PERMISSION_GRANTED
                && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED;
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            return checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
        }
        return true; // API < 23 不需要运行时权限
    }

    // ==================== 按钮事件 ====================

    private void setButtonsEnabled(boolean connected) {
        // 扫描按钮只在未连接时可用
        btnScan.setEnabled(!connected);
        btnScan.setOnClickListener(v -> {
            if (!connected) startScan();
        });

        // 以下按钮只在已连接时可用
        btnReadInfo.setEnabled(connected);
        btnRead1235.setEnabled(connected);
        btnWriteFF02.setEnabled(connected);
        btnSubscribe.setEnabled(connected);
        btnDisconnect.setEnabled(connected);

        if (connected) {
            btnReadInfo.setOnClickListener(v -> readDeviceInfo());
            btnRead1235.setOnClickListener(v -> readCharacteristic(SRV_1234, CHAR_1235, "1235"));
            btnWriteFF02.setOnClickListener(v -> writeFF02());
            btnSubscribe.setOnClickListener(v -> toggleSubscribe());
            btnDisconnect.setOnClickListener(v -> disconnect());
        }
    }

    // ==================== ① 扫描（LL: Standby → Scanning） ====================

    private void startScan() {
        if (isScanning) return;

        log("\n── 开始扫描 ──");
        log("协议：LL → Scanning State → 监听 37/38/39 信道");

        ScanSettings settings = new ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)  // 主动扫描高占空比
            .setReportDelay(0)
            .build();

        try {
            leScanner.startScan(null, settings, scanCallback);
            isScanning = true;
            tvStatus.setText("状态：扫描中...");
        } catch (SecurityException e) {
            log("❌ 缺少权限，扫描失败: " + e.getMessage());
        }
    }

    private void stopScan() {
        if (!isScanning) return;
        try {
            leScanner.stopScan(scanCallback);
            isScanning = false;
            log("停止扫描");
        } catch (SecurityException e) {
            log("❌ 权限异常: " + e.getMessage());
        }
    }

    private final ScanCallback scanCallback = new ScanCallback() {
        @Override
        public void onScanResult(int callbackType, ScanResult result) {
            BluetoothDevice device = result.getDevice();
            String name = device.getName();
            int rssi = result.getRssi();
            ScanRecord record = result.getScanRecord();

            // 解析广播数据（31 字节 AdvData — AD Structure LTV 格式）
            String advInfo = "";
            if (record != null) {
                if (record.getDeviceName() != null)
                    advInfo += " 设备名=" + record.getDeviceName();
                if (record.getTxPowerLevel() != Integer.MIN_VALUE)
                    advInfo += " TX=" + record.getTxPowerLevel() + "dBm";
            }

            log(String.format("  发现: %s [%s] RSSI=%d%s",
                name != null ? name : "(未知)",
                device.getAddress(),
                rssi,
                advInfo));

            // 自动连接 OPPO 耳机（按名称匹配）
            if (name != null && name.toLowerCase().contains("oppo")) {
                log("→ 匹配到目标设备，停止扫描并连接...");
                stopScan();
                connect(device);
            }
        }

        @Override
        public void onScanFailed(int errorCode) {
            log("❌ 扫描失败, errorCode=" + errorCode);
            isScanning = false;
        }
    };

    // ==================== ② 连接（LL: Initiating → Connection） ====================

    private void connect(BluetoothDevice device) {
        log("\n── 建立连接 ──");
        log("协议：LL → Initiating State → 发送 CONNECT_IND");
        log("      CONNECT_IND 包含: Access Address / CRC Init / Interval / Latency / Timeout / Hop");

        closeGatt();

        try {
            bluetoothGatt = device.connectGatt(this, false, gattCallback);
            tvStatus.setText("状态：连接中 → " + device.getAddress());
        } catch (SecurityException e) {
            log("❌ 缺少权限，连接失败: " + e.getMessage());
        }
    }

    // ==================== ③ GATT 回调（ATT + GATT 所有异步事件） ====================

    private final BluetoothGattCallback gattCallback = new BluetoothGattCallback() {

        // ── 连接状态变化 ──
        @Override
        public void onConnectionStateChange(BluetoothGatt gatt, int status, int newState) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                log("❌ 连接错误, status=" + status);
                return;
            }

            if (newState == BluetoothProfile.STATE_CONNECTED) {
                log("✅ 连接建立！(LL Connection State)");
                log("    下一步：requestMtu(512) → ATT EXCHANGE_MTU_REQ");
                tvStatus.setText("状态：已连接 → 协商MTU...");
                isSubscribed = false;

                try {
                    runOnUiThread(() -> gatt.requestMtu(512));
                } catch (SecurityException e) {
                    log("❌ 权限异常: " + e.getMessage());
                }
            }
            else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                log("🔌 连接断开 (LL Terminate)");
                log("    ⚠️ 此时 CCCD 已自动归零 (0x0000)");
                tvStatus.setText("状态：已断开");
                isSubscribed = false;
                runOnUiThread(() -> setButtonsEnabled(false));
            }
        }

        // ── MTU 协商完成 ──
        @Override
        public void onMtuChanged(BluetoothGatt gatt, int mtu, int status) {
            log("✅ MTU 协商完成: " + mtu + " 字节 (ATT MTU)");
            log("    有效载荷 = " + (mtu - 3) + " 字节 (MTU - 3 字节 ATT Header)");
            log("    下一步：discoverServices() → ATT READ_BY_GROUP_TYPE(0x2800)");
            tvStatus.setText("状态：MTU=" + mtu + " → 发现服务...");

            try {
                runOnUiThread(() -> gatt.discoverServices());
            } catch (SecurityException e) {
                log("❌ 权限异常: " + e.getMessage());
            }
        }

        // ── 服务发现完成 ──
        @Override
        public void onServicesDiscovered(BluetoothGatt gatt, int status) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                log("❌ 服务发现失败, status=" + status);
                return;
            }

            log("\n── 服务发现完成 ──");
            log("协议：ATT READ_BY_GROUP_TYPE → READ_BY_TYPE → FIND_INFO 三个 Round 完成");

            // 遍历打印所有 Service/Characteristic
            for (BluetoothGattService srv : gatt.getServices()) {
                String srvName = getServiceName(srv.getUuid());
                log("  📦 Service: " + srvName + " [" + srv.getUuid() + "]");
                for (BluetoothGattCharacteristic ch : srv.getCharacteristics()) {
                    String props = getPropertyString(ch.getProperties());
                    log("      ↳ Char: " + ch.getUuid() + " [" + props + "]");
                    for (BluetoothGattDescriptor desc : ch.getDescriptors()) {
                        log("          ↳ Desc: " + desc.getUuid());
                    }
                }
            }

            tvStatus.setText("状态：已连接，服务发现完成 ✓");
            runOnUiThread(() -> setButtonsEnabled(true));
        }

        // ── 特征值读取完成 ──
        @Override
        public void onCharacteristicRead(BluetoothGatt gatt,
                                          BluetoothGattCharacteristic ch, int status) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                log("  ❌ 读取失败, status=" + status + " (可能需加密/认证)");
                return;
            }
            byte[] value = ch.getValue();
            String hex = bytesToHex(value);
            String utf8 = tryUtf8(value);
            log("  ✅ 读取 " + ch.getUuid() + " = " + hex + (utf8 != null ? " (\"" + utf8 + "\")" : ""));
        }

        // ── 特征值写入完成 ──
        @Override
        public void onCharacteristicWrite(BluetoothGatt gatt,
                                           BluetoothGattCharacteristic ch, int status) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                log("  ❌ 写入失败, status=" + status);
                return;
            }
            log("  ✅ 写入成功 " + ch.getUuid() + " = " + bytesToHex(ch.getValue()));
        }

        // ── 收到通知/指示（★ 核心：ATT HANDLE_VALUE_NOTIFICATION/INDICATION） ──
        @Override
        public void onCharacteristicChanged(BluetoothGatt gatt,
                                             BluetoothGattCharacteristic ch) {
            byte[] value = ch.getValue();
            log("  🔔 通知! " + ch.getUuid() + " = " + bytesToHex(value)
                + "  (ATT HANDLE_VALUE_NOTIFICATION, 无需确认)");
        }

        // ── Descriptor 写入完成（CCCD 写完后回调） ──
        @Override
        public void onDescriptorWrite(BluetoothGatt gatt,
                                       BluetoothGattDescriptor desc, int status) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                log("  ❌ CCCD 写入失败, status=" + status);
                return;
            }
            log("  ✅ CCCD 写入成功 → 通知已" + (isSubscribed ? "开启" : "关闭"));
            log("     (ATT WRITE_REQ → CCCD=0x" + (isSubscribed ? "0001" : "0000") + ")");
        }
    };

    // ==================== ④ 读取设备信息（ATT READ_REQ） ====================

    private void readDeviceInfo() {
        log("\n── 读取 Device Information ──");
        log("协议：ATT READ_REQ → ATT READ_RSP（每读一个特征值一次往返）");

        BluetoothGattService dis = bluetoothGatt.getService(SRV_DEVICE_INFO);
        if (dis == null) {
            log("❌ Device Information Service 未找到");
            return;
        }

        readChar(dis, CHAR_MANUFACTURER, "制造商");
        readChar(dis, CHAR_FIRMWARE_REV,   "固件版本");
        readChar(dis, CHAR_MODEL_NUMBER,   "型号");
    }

    private void readChar(BluetoothGattService srv, UUID charUuid, String label) {
        BluetoothGattCharacteristic ch = srv.getCharacteristic(charUuid);
        if (ch == null) {
            log("  ⚠️ " + label + " 特征值不存在");
            return;
        }
        log("  → 请求读取 " + label + " (" + charUuid + ")");
        try {
            bluetoothGatt.readCharacteristic(ch);
        } catch (SecurityException e) {
            log("  ❌ 权限异常: " + e.getMessage());
        }
    }

    private void readCharacteristic(UUID srvUuid, UUID charUuid, String label) {
        log("\n── 读取 " + label + " ──");
        BluetoothGattService srv = bluetoothGatt.getService(srvUuid);
        if (srv == null) {
            log("❌ Service 未找到: " + srvUuid);
            return;
        }
        BluetoothGattCharacteristic ch = srv.getCharacteristic(charUuid);
        if (ch == null) {
            log("❌ Characteristic 未找到: " + charUuid);
            return;
        }
        log("  → ATT READ_REQ → " + charUuid);
        try {
            bluetoothGatt.readCharacteristic(ch);
        } catch (SecurityException e) {
            log("  ❌ 权限异常: " + e.getMessage());
        }
    }

    // ==================== ⑤ 写 FF02（ATT WRITE_CMD，无确认） ====================

    /**
     * ⚠️ 警告：厂商私有 Characteristic，写入可能触发耳机实际行为
     * （如 ANC 开关、触控配置、EQ 调节等）。
     * 这里写入安全测试值 0x01，仅用于观察协议流程。
     */
    private void writeFF02() {
        log("\n── 写入 FF02（ATT WRITE_CMD，无确认）──");
        BluetoothGattService srv = bluetoothGatt.getService(SRV_FF00);
        if (srv == null) { log("❌ Service FF00 未找到"); return; }

        BluetoothGattCharacteristic ch = srv.getCharacteristic(CHAR_FF02);
        if (ch == null) { log("❌ FF02 未找到"); return; }

        ch.setWriteType(BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE);
        ch.setValue(new byte[]{0x01});
        log("  → ATT WRITE_CMD, value=0x01 (无响应，发送即成功)");
        try {
            bluetoothGatt.writeCharacteristic(ch);
        } catch (SecurityException e) {
            log("  ❌ 权限异常: " + e.getMessage());
        }
    }

    // ==================== ⑥ 订阅/取消订阅 1236 通知 ====================

    /**
     * ★ 这是整个 App 最重要的练习！
     *   设置 Characteristic Notification + 写 CCCD 两步共同实现通知订阅。
     *   重连后 CCCD 自动归零 → 必须重新调用此方法。
     */
    private void toggleSubscribe() {
        BluetoothGattService srv = bluetoothGatt.getService(SRV_1234);
        if (srv == null) { log("❌ Service 1234 未找到"); return; }

        BluetoothGattCharacteristic ch = srv.getCharacteristic(CHAR_1236);
        if (ch == null) { log("❌ 1236 未找到"); return; }

        if ((ch.getProperties() & BluetoothGattCharacteristic.PROPERTY_NOTIFY) == 0
         && (ch.getProperties() & BluetoothGattCharacteristic.PROPERTY_INDICATE) == 0) {
            log("❌ 1236 不支持 NOTIFY/INDICATE");
            return;
        }

        isSubscribed = !isSubscribed;

        try {
            if (isSubscribed) {
                log("\n── 订阅 1236 通知 ──");
                log("  ① setCharacteristicNotification(ch, true)");
                log("     → 告诉 Android 蓝牙栈：收到此 Handle 的通知请回调我");

                bluetoothGatt.setCharacteristicNotification(ch, true);

                BluetoothGattDescriptor cccd = ch.getDescriptor(CCCD);
                if (cccd == null) {
                    log("  ❌ CCCD Descriptor 未找到！这是异常情况");
                    isSubscribed = false;
                    return;
                }

                log("  ② writeDescriptor(CCCD=0x0001)");
                log("     → ATT WRITE_REQ, 写入 CCCD=0x0001 开启通知");
                log("     → 设备收到后开始发 ATT HANDLE_VALUE_NOTIFICATION");

                cccd.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
                bluetoothGatt.writeDescriptor(cccd);

                btnSubscribe.setText("🔕 取消订阅");
            } else {
                log("\n── 取消订阅 1236 ──");
                BluetoothGattDescriptor cccd = ch.getDescriptor(CCCD);
                if (cccd != null) {
                    cccd.setValue(BluetoothGattDescriptor.DISABLE_NOTIFICATION_VALUE);
                    bluetoothGatt.writeDescriptor(cccd);
                }
                bluetoothGatt.setCharacteristicNotification(ch, false);
                btnSubscribe.setText("🔔 订阅1236");
            }
        } catch (SecurityException e) {
            log("  ❌ 权限异常: " + e.getMessage());
            isSubscribed = false;
        }
    }

    // ==================== ⑦ 断开（LL TERMINATE_IND） ====================

    private void disconnect() {
        log("\n── 断开连接 ──");
        log("协议：LL LL_TERMINATE_IND → Connection → Standby");
        log("     ⚠️ 断开后 CCCD 自动归零 (0x0000)");
        log("     ⚠️ 重连后若不重写CCCD，即使设备发通知，手机也收不到！");
        closeGatt();
        isSubscribed = false;
        setButtonsEnabled(false);
    }

    private void closeGatt() {
        if (bluetoothGatt != null) {
            try {
                bluetoothGatt.disconnect();
                bluetoothGatt.close();
            } catch (SecurityException e) {
                log("❌ 断开异常: " + e.getMessage());
            }
            bluetoothGatt = null;
        }
    }

    // ==================== 工具方法 ====================

    private void log(String msg) {
        Log.d(TAG, msg);
        logBuilder.append(msg).append("\n");
        runOnUiThread(() -> {
            tvLog.setText(logBuilder.toString());
            // 自动滚到底部
            scrollLog.post(() -> scrollLog.fullScroll(View.FOCUS_DOWN));
        });
    }

    private String bytesToHex(byte[] bytes) {
        if (bytes == null || bytes.length == 0) return "(空)";
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) sb.append(String.format("%02X ", b));
        return sb.toString().trim();
    }

    private String tryUtf8(byte[] bytes) {
        try {
            String s = new String(bytes, "UTF-8");
            // 只返回可打印字符串
            return s.matches("^[\\x20-\\x7E\\p{IsHan}]+$") ? s : null;
        } catch (Exception e) { return null; }
    }

    private String getServiceName(UUID uuid) {
        // 标准 Service 名称映射
        if (uuid.equals(UUID.fromString("00001800-0000-1000-8000-00805f9b34fb"))) return "Generic Access";
        if (uuid.equals(UUID.fromString("00001801-0000-1000-8000-00805f9b34fb"))) return "Generic Attribute";
        if (uuid.equals(UUID.fromString("0000180a-0000-1000-8000-00805f9b34fb"))) return "Device Information";
        if (uuid.equals(SRV_FF00))  return "厂商自定义 (FF00)";
        if (uuid.equals(SRV_1234))  return "厂商自定义 (1234)";
        return "未知 Service";
    }

    private String getPropertyString(int props) {
        List<String> list = new ArrayList<>();
        if ((props & BluetoothGattCharacteristic.PROPERTY_READ) != 0)               list.add("READ");
        if ((props & BluetoothGattCharacteristic.PROPERTY_WRITE) != 0)              list.add("WRITE");
        if ((props & BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE) != 0)  list.add("WRITE_NO_RSP");
        if ((props & BluetoothGattCharacteristic.PROPERTY_NOTIFY) != 0)             list.add("NOTIFY");
        if ((props & BluetoothGattCharacteristic.PROPERTY_INDICATE) != 0)           list.add("INDICATE");
        return String.join(", ", list);
    }
}
