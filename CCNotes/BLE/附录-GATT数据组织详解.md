# 附录 — GATT 数据组织详解

> 从零开始搭一个 GATT Server，彻底搞懂数据到底怎么存、怎么查。

---

## 核心认知翻转

**GATT 不是树，是一张平面表。层级关系是通过特殊 UUID 标签"标注"出来的。**

说人话：Server 只有一张数组——每一行有 Handle、Type(UUID)、Value。你读到的"Service/Characteristic/Descriptor"三层嵌套结构，是 Client 读取这张表后，根据某些行的 UUID 标签**推断重建**出来的。

---

## 第一步：最简单的表——只有一行数据

假设我是一个温度计 GATT Server，我只在内存里维护一行属性：

```
Handle   Type(UUID)   Value        Permissions
─────────────────────────────────────────────
0x0001   0x2A6E      0xEB 0x00     Read
```

- Handle = 行号，从 0x0001 开始递增
- Type = 这一行存的是什么（0x2A6E = Temperature Measurement，蓝牙 SIG 定义的）
- Value = 实际数据（0x00EB = 23.5°C，按规范格式存的）
- Permissions = 谁能读写这一行

Client 知道 Handle=0x0001 的话，发 Read Request → 拿到 0xEB 0x00 → 查规范知道 0x2A6E 编码格式 → 算出 23.5°C。

**这就是 GATT 的全部——一张带权限的键值表。到此为止没有任何层级结构。**

---

## 第二步：但 Client 不知道 Handle 怎么办？

Client 第一次连上，根本不知道温度值在 Handle 0x0001。它问 Server：

"请告诉我你有哪些行？"

Server 没理由拒绝——但这只是简单的数组遍历，ATT 的 Read By Type Request 就干这个。Client 指定一个 UUID，Server 返回所有匹配的行。

问题在于：**如果设备有 50 行属性，Client 就要遍历 50 次才能看完。而且 Client 不知道哪几行属于同一个"功能模块"。**

---

## 第三步：引入 0x2800 —— Service 标签行

Server 在表里插入一行"标记行"，告诉 Client："从这一行开始，到某一行结束，是一个功能模块"。

```
Handle   Type(UUID)   Value                    Permissions
───────────────────────────────────────────────────────────
0x0001   0x2800      0x001E  0x1809            Read
0x0002   0x2A6E      0xEB 0x00                 Read
```

第 0x0001 行是一行**元数据**——Type = 0x2800 的含义是"这是一条服务声明"。

它的 Value 是两段数据：

```
Byte 0-1: 0x001E → End Group Handle（这个服务到 0x001E 结束）
Byte 2-3: 0x1809 → Health Thermometer Service（这个服务的类型是体温计）
```

所以 0x0001 这行的**语义**是：

> "从我的 Handle (0x0001) 到 Handle 0x001E，是一个 Health Thermometer Service"

Client 读表时看到 Type=0x2800，就知道：
- 这是服务边界标记
- Value 前 2 字节 = 结束 Handle
- Value 后 2 字节 = 服务类型

**一行 Type=0x2800 的属性 = 一个 SVG 中的 `<g id="thermometer">` 注释**。它不存数据，只是给 Client 看的声明。

---

## 第四步：引入 0x2803 —— Characteristic 标签行

Service 范围内可能有多个特征（温度值、测量间隔、传感器位置……），每个特征需要自己的标签行：

```
Handle   Type(UUID)   Value                              Permissions
─────────────────────────────────────────────────────────────────────
0x0001   0x2800      0x00 0x1E  0x09 0x18              Read        ← Service 声明
0x0002   0x2803      02  03 00  6E 2A                   Read        ← Characteristic 声明
0x0003   0x2A6E      0xEB 0x00                           Read        ← 温度值
0x0004   0x2803      08  05 00  1C 2A                   Read        ← Characteristic 声明
0x0005   0x2A1C      0xF4 0x01                           Read+Write  ← 测量间隔
...
0x001E   (某行标记)                                       ...         ← Service 结束
```

0x2803 行的 Value 结构是固定的：

```
Byte 0:    Properties（0x02=Read, 0x08=Write, 0x10=Notify...）
Byte 1-2:  Value Handle（这个特征的值存在哪一行）
Byte 3-4:  Characteristic UUID（这个特征是什么类型）
```

所以 Handle 0x0002 这行的语义是：

> "下一个特征：支持 Read 操作，值在 Handle 0x0003，类型是 Temperature Measurement (0x2A6E)"

**一行 Type=0x2803 的属性 = 一个 C struct 的字段声明 `uint16 temperature; // 存在地址 0x0003`。它不是数据，是元数据。**

---

## 第五步：引入 0x2902 —— CCCD

如果一个 Characteristic 的 Properties 包含 Notify/Indicate，Server 需要一个开关让 Client 控制是否推送。这个开关是一个普通的可写行：

```
Handle   Type(UUID)   Value       Permissions
─────────────────────────────────────────────
0x0002   0x2803      10  03 00  6E 2A   Read          ← Properties=0x10=Notify
0x0003   0x2A6E      0xEB 0x00           Read          ← 温度值（可通知）
0x0004   0x2902      0x00 0x00           Read+Write    ← CCCD 开关
```

0x2902 行的语义：

> "我是 Handle 0x0003 的通知开关。写 0x0001 = 开通知，写 0x0000 = 关通知。断开自动归零。"

在 GATT 规范中，CCCD 的位置是**约定俗成**的——它跟着前一个 Characteristic 的 Value 行之后。Client 服务发现时会顺着 Handle 往下找。

---

## 第六步：全部行展开

现在把体温计服务的所有行完整写出来——这就是 Server 在内存里的东西，就这么多，没有"树"：

```
Handle  Type    Value(hex)                          解读（Client 解析后）
────────────────────────────────────────────────────────────────────────────
0x0001  0x2800 1E 00  09 18                         声明：Service(0x1809)，结束于 Handle=0x001E
0x0002  0x2803 10  03 00  1C 2A                      声明：特征 Prop=Notify, Handle=0x0003, UUID=0x2A1C (温度类型)
0x0003  0x2A1C 02                                   值：温度类型 = 耳朵 (0x02)
0x0004  0x2803 10  05 00  6E 2A                      声明：特征 Prop=Notify, Handle=0x0005, UUID=0x2A6E (温度值)
0x0005  0x2A6E 06 78 00 3C 21                        值：温度 = 37.8°C (带时间戳)
0x0006  0x2902 00 00                                CCCD：通知开关（关→0x0005 的值不会被推送）
0x0007  0x2803 0A  08 00  24 2A                      声明：特征 Prop=Read+Write, Handle=0x0008, UUID=0x2A24 (测量间隔)
0x0008  0x2A24 3C 00                                值：测量间隔 = 60 秒
0x0009  ...                                         
...                                                
0x001E  (下一行的 Handle 就是 0x001F)                 ← Service 边界结束
```

---

## 第七步：Client 怎么"发现"结构

Client 连上后，没有树、没有文件夹、只有一个 Handle 范围的概念。它做三件事：

### Round 1：找所有 0x2800（Service 声明）

```
Read By Group Type Request: Type=0x2800, Range=0x0001~0xFFFF
→ 返回:
  Handle=0x0001, EndGroup=0x001E, UUID=0x1809  (Health Thermometer)
  Handle=0x001F, EndGroup=0x0030, UUID=0x180A  (Device Information)
  Handle=0x0031, EndGroup=0x0040, UUID=0x180F  (Battery Service)
```

Client 现在有了"文件夹列表"：

```
├── 0x0001~0x001E  Health Thermometer (0x1809)
├── 0x001F~0x0030  Device Information (0x180A)
└── 0x0031~0x0040  Battery Service   (0x180F)
```

### Round 2：在每个 Service 范围内找所有 0x2803（Characteristic 声明）

```
在 0x0002~0x001E 范围内:
Read By Type Request: Type=0x2803
→ 返回:
  Handle=0x0002, Value=[10 03 00 1C 2A]  (Notify, 值在 0x0003, UUID=0x2A1C)
  Handle=0x0004, Value=[10 05 00 6E 2A]  (Notify, 值在 0x0005, UUID=0x2A6E)
  Handle=0x0007, Value=[0A 08 00 24 2A]  (ReadWrite, 值在 0x0008, UUID=0x2A24)
```

Client 现在有了"文件列表"：

```
Health Thermometer (0x1809):
├── Handle 0x0002 → [数据在 0x0003, 类型 0x2A1C]  温度类型（Notify）
├── Handle 0x0004 → [数据在 0x0005, 类型 0x2A6E]  温度值（Notify）
└── Handle 0x0007 → [数据在 0x0008, 类型 0x2A24]  测量间隔（Read+Write）
```

### Round 3：在每个 Characteristic 的 Value Handle 附近找 Descriptor

```
在 0x0003~0x0003 范围内: 无 Descriptor
在 0x0005~0x0005 范围内: 往下一行找到 0x0006, Type=0x2902 → CCCD
在 0x0008~0x0008 范围内: 无 Descriptor
```

### 全部发现完成——Client 在内存中重建的"树"：

```
Health Thermometer Service (0x1809)
├── Temperature Type (0x2A1C)
│   └── Value @ 0x0003 (Notify, 无 CCCD? 实际上规范里这个特征不需要 CCCD)
├── Temperature Measurement (0x2A6E)
│   ├── Value @ 0x0005 (Notify)
│   └── CCCD @ 0x0006 (控制通知开关)
└── Measurement Interval (0x2A24)
    └── Value @ 0x0008 (Read + Write)
```

**这个树只有 Client 内存里有。Server 那边永远是那张平表。**

---

## 核心要点重述

1. **Server 只存一张表**，Handle 递增，每一行 = (Type UUID, Value bytes, Permissions)
2. **Type 决定这行的角色**：0x2800 = 服务声明 / 0x2803 = 特征声明 / 0x2xxx = 数据 / 0x29xx = 描述符
3. **声明行的 Value 是元数据**：给出下一行的 Handle、功能类型、访问方式
4. **Client 通过按 UUID 筛选来"发现"结构**：先进 0x2800 拿到所有服务边界，然后 0x2803 拿每个服务的所有特征，最后 0x2902 拿 CCCD
5. **层级关系是 Client 根据声明行的内容推断出来的**，空中从来不会传"树"——只传平面行

---

## ATT 和 GATT 的分工

```
GATT（数据模型）：定义了"声明行 → 数据行"的编码规则
                 0x2800 的 Value 格式是什么？0x2803 的 Properties 位域怎么解码？
                 标准 UUID 每个表示什么类型的服务/特征？

ATT（传输协议）：定义了 Client 怎么查/读/写这些行的指令
                 Read By Type Request → Response
                 Read Request → Response
                 Write Request → Response
                 Handle Value Notification
```

GATT = 文件夹结构和文件命名规则，ATT = 操作系统提供的文件操作 API (open/read/write/seek)。

---

## 附录 A：UUID 到底是什么

### UUID 是类型的身份证号

你看到一个 UUID，查表就知道"这行属性存的是什么数据"。0x180D 永远是 Heart Rate Service，0x2A37 永远是 Heart Rate Measurement，全球所有设备共用。

### 16 位 UUID（蓝牙 SIG 分配）

蓝牙官方组织预定义，所有厂商共用。换算关系——16 位 UUID 填入蓝牙基地址：

```
0000XXXX-0000-1000-8000-00805F9B34FB
    ↑
    16 位 UUID 填在这里

示例：0x2A37 →
00002A37-0000-1000-8000-00805F9B34FB
```

反过来，看到一个 128 位 UUID 中间是 `0000-1000-8000-00805F9B34FB`，前面的 16 位就是标准 ID。

### 128 位 UUID（厂商自定义）

厂商自己生成随机 128 位 UUID，用来标识私有服务/特征。常见做法是生成一个基地址，然后偏移派生：

```
基础 UUID:  A1B2C3D4-0000-1000-8000-00805F9B34FB

服务 UUID  : A1B2C3D4-0000-1000-8000-00805F9B34FB  ← 基地址就是服务 UUID
特征1 UUID : A1B2C3D4-0001-1000-8000-00805F9B34FB  ← 收客户端消息
特征2 UUID : A1B2C3D4-0002-1000-8000-00805F9B34FB  ← 通知客户端
```

所有 UUID 共享同一个前缀，一看就知道是一家。Nordic、TI 都是这么干的。

### Declaration 的特殊 UUID

Handle 表中有些行的 UUID 不是数据，是**元数据标签**：

| UUID | 含义 | Value 里存什么 |
|------|------|--------------|
| 0x2800 | Primary Service Declaration | 服务的 UUID（如 0x180D） |
| 0x2801 | Secondary Service Declaration | 次级服务的 UUID |
| 0x2802 | Include Declaration | 引用其他 Service |
| 0x2803 | Characteristic Declaration | Properties + Value Handle + 特征 UUID |

### 常见标准 UUID 速查

**Service UUID：**

| UUID | 服务名称 | 实际设备 |
|------|---------|---------|
| 0x1800 | Generic Access | 所有设备 |
| 0x1801 | Generic Attribute | 所有设备 |
| 0x180A | Device Information | 所有设备 |
| 0x180D | Heart Rate | 心率带 |
| 0x180F | Battery Service | 耳机、手环 |
| 0x1809 | Health Thermometer | 体温计 |

**Characteristic UUID：**

| UUID | 特征名称 | 里面存什么 |
|------|---------|----------|
| 0x2A00 | Device Name | "Galaxy Watch5" |
| 0x2A19 | Battery Level | 85（%） |
| 0x2A29 | Manufacturer Name String | "Samsung" |
| 0x2A37 | Heart Rate Measurement | Flag + bpm + RR 间隔 |
| 0x2A38 | Body Sensor Location | 0x02 = Wrist |
| 0x2A39 | Heart Rate Control Point | 0x01 = 重置能量 |

**Descriptor UUID：**

| UUID | 描述符名称 | 用途 |
|------|----------|------|
| 0x2900 | Characteristic Extended Properties | 扩展属性标志 |
| 0x2901 | Characteristic User Description | "心率值（次/分钟）" |
| 0x2902 | CCCD | 通知/指示开关 |
| 0x2904 | Characteristic Presentation Format | 数据格式描述（单位、指数等） |

### 二进制传输，不是 ASCII

服务发现时空中传输的是纯二进制，全程没有字符串转换。举个例子——Characteristic Declaration（UUID=0x2803）在空中：

```
Byte 0:   0x10          ← Properties (Notify)
Byte 1:   0x12          ← Value Handle 低字节
Byte 2:   0x00          ← Value Handle 高字节        → 0x0012
Byte 3:   0x37          ← Characteristic UUID 低字节
Byte 4:   0x2A          ← Characteristic UUID 高字节  → 0x2A37
```

Client 用固定偏移拆包，拿到 UUID = 0x2A37 后在本地查表 → "心率测量值"。语义完全在 Client 端重建，空中不传"心率"二字。

---

## 附录 B：厂商自定义服务设计指南

### 场景：一个服务 + 两个特征

- 特征 1：接收客户端消息（C→S，要求确认送达）
- 特征 2：推送通知给客户端（S→C）

### 第一步：确定 Properties

**特征 1（收消息）：**

| 选项 | ATT 指令 | 特点 |
|------|---------|------|
| Write Request (0x12) | 需回复 Write Response | 可靠送达确认，慢 |
| Write Command (0x52) | 无回复 | 快但不保证 |
| 两个都支持 | 设 Properties = 0x0C | Client 按消息类型自选 |

如果每条消息都需要确认 → 用 Write Request。

**特征 2（推消息）：**

| 选项 | ATT 指令 | 特点 |
|------|---------|------|
| Notification (0x1B) | 不等待确认 | 速度快，可丢 |
| Indication (0x1D) | Client 必须回 Confirmation | 送达保证 |

**特征 2 必须配 CCCD（0x2902）**，Client 写 CCCD 才能订阅推送。

### 第二步：确定 UUID

用 128 位 UUID，基地址 + 偏移：

```
Base:     A1B2C3D4-0000-1000-8000-00805F9B34FB
Service:  A1B2C3D4-0000-1000-8000-00805F9B34FB
特征1:    A1B2C3D4-0001-1000-8000-00805F9B34FB
特征2:    A1B2C3D4-0002-1000-8000-00805F9B34FB
```

### 第三步：确定是否需要加密

如果消息含敏感数据（密码、校准参数），特征 1 的权限设 **Encryption Required**。加密触发权在 GATT 权限表——App 不手动调加密，协议栈检测到权限不够时自动触发。

### 第四步：确定业务协议

协议层只保证字节送到。业务层用**序列号**实现请求-响应匹配：

```
Client → Server (Write Request):
Byte 0:   序列号（0x01）
Byte 1:   命令码（0x03 = 改采样频率）
Byte 2-3: 参数（0x00 0x3C = 60）

Server → Client (Notification):
Byte 0:   序列号（0x01）  ← 和请求一样，Client 用来匹配
Byte 1:   状态码（0x00 = 成功 / 0x01 = 参数非法 / 0x02 = 设备忙）
Byte 2-n: 可选扩展数据
```

### 完整的属性表

```
Handle  Type      Value / 含义
──────────────────────────────────────────────────────────────────
0x0001  0x2800    Service Declaration
                 → EndGroupHandle = 0x0007
                 → UUID = A1B2C3D4-0000-1000-8000-00805F9B34FB

0x0002  0x2803    Characteristic Declaration（收消息）
                 → Properties = Write(0x08) = 0x08
                 → Value Handle = 0x0003
                 → UUID = A1B2C3D4-0001-1000-8000-00805F9B34FB

0x0003  自定义    Value（收发数据在这里）
                 → Permissions: Write
                 → 可能设 Encryption Required

0x0004  0x2803    Characteristic Declaration（推消息）
                 → Properties = Notify(0x10)
                 → Value Handle = 0x0005
                 → UUID = A1B2C3D4-0002-1000-8000-00805F9B34FB

0x0005  自定义    Value（推送数据在这里）
                 → Permissions: Read

0x0006  0x2902    CCCD
                 → Permissions: Read + Write
                 → Client 写 0x0001 开启通知

0x0007  ───      服务结束
```

### 常见疑问

**Q: 特征 1 需要 CCCD 吗？**
不需要。CCCD 只服务于 Notify/Indicate。Write 特征没有"订阅"概念，Client 直接写就行。

**Q: 特征 2 的 Value Handle 权限需要设 Read 吗？**
建议设。虽然数据主要靠推送，但 Client 偶尔想主动读最新值（通知还没来时）就多个路径。

**Q: 建议配 User Description (0x2901) 吗？**
建议配。存一段人类可读字符串（"Command Channel" / "Data Channel"），调试和兼容性测试时极其有用。

---

## 附录 C：链路层 ACK ≠ ATT 层确认

这是 BLE 中最容易混淆的概念。

### 两层确认，各自独立

```
┌──────────────────────────────────────────┐
│  ATT 层                                  │
│  ┌─────────────────────────────────────┐ │
│  │ Write Request (0x12)                 │ │
│  │    → 必须回 Write Response (0x13)    │ │  ← ATT 层确认
│  │                                      │ │     "属性表写入成功"
│  │ Write Command (0x52)                 │ │
│  │    → 不回任何东西                     │ │  ← 无 ATT 层确认
│  └─────────────────────────────────────┘ │
│                    ↓                     │
│               L2CAP 封装                  │
│                    ↓                     │
├──────────────────────────────────────────┤
│  链路层 (Link Layer)                      │
│  ┌─────────────────────────────────────┐ │
│  │ 每一个数据包，不管里面装的是什么        │ │
│  │ (Write Request / Write Command /     │ │
│  │  Notification / 空包 ...)             │ │
│  │                                      │ │
│  │ 接收方 150μs 内必须回 ACK            │ │  ← 链路层确认
│  │                                      │ │     "无线电包 CRC 校验通过"  │
│  └─────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

### 链路层 ACK 是什么

是快递公司的签收扫描——"外包装完好"。150μs 内就发出了。

### ATT Write Response 是什么

是收货人签字的回执单——"东西入库了"。只有 Write Request 有。

### 关键：链路层 ACK 之后还可能失败

ACK 发出后，数据还要经过这些步骤：

```
0μs       150μs                             1ms+
│         │                                 │
│ 包到达   │ 链路层 ACK 已发出 ✅              │
│         │                                 │
│         ↓                                 ↓
│    ┌──────────────────────────────────────────┐
│    │ 1. 链路层 → 把 Payload 交给 L2CAP       │
│    │ 2. L2CAP 重组（如果分片了）              │  ← ACK 之后发生的
│    │ 3. L2CAP → 根据 CID 交给 ATT            │
│    │ 4. ATT 层解析 Opcode                    │
│    │ 5. ATT 层检查 Handle 是否存在            │
│    │ 6. ATT 层检查 Permissions 是否允许写入    │  ← 这些都可能失败
│    │ 7. ATT 层写入属性表                      │
│    │ 8. 如果权限不够、Handle 不存在、         │
│    │    属性表满了…… → 会报错！               │
│    └──────────────────────────────────────────┘
```

### 实例：包没坏，但写失败了

Client 发了一条 Write Command：

```
Opcode: 0x52 (Write Command)
Handle: 0x9999    ← 不存在！
Value:  [一些数据]
```

时间线：

1. 链路层：CRC 校验通过 → **回 ACK ✅**（150μs 内）
2. 协议栈往上送，到 ATT 层一查：Handle 0x9999 不存在
3. **写失败了，静默丢弃**

**Client 知道吗？不知道。** ACK 已经回了，Write Command 没有 ATT 层回复。Client 以为成功。

**如果用的是 Write Request**：Server ATT 层发现 Handle 不存在 → 回 **Error Response**（Opcode 0x01，错误码 0x01 = Invalid Handle）。Client 才知道出了问题。

### Write Request vs Write Command 最终对比

| | Write Request | Write Command |
|---|---|---|
| ATT Opcode | 0x12 | 0x52 |
| 链路层 ACK | 有（所有包都有） | 有（所有包都有） |
| ATT 层回复 | Write Response (0x13) 或 Error Response (0x01) | **无** |
| Client 知道写成功了？ | ✅ Write Response 确认 | ❌ 不知道 |
| Client 知道写失败了？ | ✅ Error Response 告知原因 | ❌ 不知道，静默丢 |
| 适用场景 | 配置参数、命令（需确认） | 流式数据、实时控制（吞吐优先） |

### 用 Write Response 确认"送达"的时间线

```
Client                          Server
  │                               │
  │──── Write Request ───────────→│  ① Client 发出数据
  │                               │  ② Server 链路层回 ACK（150μs 内）
  │                               │  ③ ATT 层写入属性表
  │←── Write Response ───────────│  ④ ATT 层回 Response
  │                               │  ⑤ GATT 回调触发，通知 App
  │                               │  ⑥ App 解析命令、执行业务操作
  │                               │  ⑦ App 构造结果，写 Notification
  │←── Notification ────────────│  ⑧ 业务层结果返回
```

**Write Response 在第 ④ 步就发出去了，那时 App 连回调都还没收到。** 它只证明"字节成功写入属性表"，不证明"活干完了"。业务结果靠第 ⑧ 步的 Notification 来保证。

### 一句话总结

| 层次 | 叫什么 | 谁发的 | 出现条件 | 保证什么 |
|------|--------|--------|---------|---------|
| 链路层 | ACK | Controller 硬件 | **所有包**都有 | 无线电包 CRC 校验通过 |
| ATT 层 | Write Response / Error Response | Server 协议栈 | 只有 Write Request 有 | 数据写入属性表成功 / 写入失败 + 原因 |
