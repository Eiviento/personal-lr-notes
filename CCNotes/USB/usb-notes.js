// usb-notes.js
// USB 协议学习笔记 — 数据层 + 渲染层
//
// 3 文件翻新架构（HTML/CSS/JS）中的 JS 文件，本文件为 JS 第 1-2 模块：
// DATA（数据层）+ RENDERERS（渲染层）。
// PACKET_DATA 与 FRAME_TRANSACTIONS 从旧版 usb-notes.html 逐字提取，内容不变。
// 交互层（ThemeManager/ScrollSpy/SearchFilter/NavOverlay）与初始化入口由后续任务追加。

// ===== 1. DATA =====

// PACKET_COLORS 映射（从旧文件复制）
var PACKET_COLORS = {
  'sync-pid': 'color-sync-pid',
  'addr':     'color-addr',
  'data':     'color-data',
  'crc':      'color-crc',
  'eop':      'color-eop',
  'frame':    'color-frame',
};

// PACKET_DATA — 4 个包结构图数据（完整复制旧文件内容）
var PACKET_DATA = [
  {
    id: 'pkt-token',
    title: 'Token 包 (IN/OUT/SETUP) — 共 35 bits',
    fields: [
      { name: 'SYNC',     bits: 8, val: '00000001', desc: '同步序列, LSB first。7个0让接收方PLL锁定时钟', color: 'sync-pid' },
      { name: 'PID',      bits: 8, val: 'IN=0x69, OUT=0xE1, SETUP=0x2D', desc: '包标识符, 高4位=~低4位。IN=1001, OUT=0001, SETUP=1101', color: 'sync-pid' },
      { name: 'ADDR',     bits: 7, val: '0x01~0x7F', desc: '设备地址。7bit → 128个, 0x00保留, 可分配1~127。Host分配地址, 设备被动接受', color: 'addr' },
      { name: 'ENDP',     bits: 4, val: '0x0~0xF', desc: '端点号。4bit → 0~15。EP0固定用于控制传输', color: 'addr' },
      { name: 'CRC5',     bits: 5, val: '校验和', desc: '多项式 x⁵+x²+1 (0x25), 校验范围 ADDR(7b)+ENDP(4b)=11bits。CRC5不匹配→地址或端点号损坏→丢弃包', color: 'crc' },
      { name: 'EOP',      bits: 3, val: 'SE0+J', desc: '包结束信号。SE0持续2个bit时间 + J状态1个bit时间', color: 'eop' },
    ]
  },
  {
    id: 'pkt-sof',
    title: 'SOF Token 包 — 共 35 bits',
    fields: [
      { name: 'SYNC',     bits: 8, val: '00000001', desc: '同步序列, LSB first', color: 'sync-pid' },
      { name: 'PID',      bits: 8, val: 'SOF=0xA5', desc: 'SOF PID=0101(低4位)→0xA5。SOF无ADDR/ENDP, 是广播包', color: 'sync-pid' },
      { name: 'Frame #',  bits:11, val: '0x000~0x7FF', desc: '帧号。11bit → 0~2047。FS: 1ms一帧→2.048s回卷。HS: 125μs微帧→每8微帧才+1', color: 'frame' },
      { name: 'CRC5',     bits: 5, val: '校验和', desc: '多项式 x⁵+x²+1, 校验11bit帧号', color: 'crc' },
      { name: 'EOP',      bits: 3, val: 'SE0+J', desc: '包结束信号', color: 'eop' },
    ]
  },
  {
    id: 'pkt-data',
    title: 'Data 包 (DATA0/DATA1/DATA2/MDATA) — 27 + 0~8192 bits',
    fields: [
      { name: 'SYNC',     bits: 8, val: '00000001', desc: '同步序列', color: 'sync-pid' },
      { name: 'PID',      bits: 8, val: 'DATA0=0xC3, DATA1=0x4B', desc: 'DATA0(0011)/DATA1(1011)/DATA2(0111)/MDATA(1111)。Toggle翻转区分重传和新数据', color: 'sync-pid' },
      { name: 'DATA',     bits: 0, val: '0~1024 Bytes', desc: '有效载荷。0B时Data包只含PID+CRC16。>MaxPacketSize的载荷被拆成多个Data包', color: 'data', flexFactor: 8 },
      { name: 'CRC16',    bits:16, val: '校验和', desc: '多项式 x¹⁶+x¹⁵+x²+1 (0x8005)。校验范围: DATA字段全部字节。16bit能检测几乎所有多bit错误', color: 'crc' },
      { name: 'EOP',      bits: 3, val: 'SE0+J', desc: '包结束信号', color: 'eop' },
    ]
  },
  {
    id: 'pkt-handshake',
    title: 'Handshake 包 (ACK/NAK/STALL/NYET) — 共 19 bits',
    fields: [
      { name: 'SYNC',     bits: 8, val: '00000001', desc: '同步序列', color: 'sync-pid' },
      { name: 'PID',      bits: 8, val: 'ACK=0xD2, NAK=0x5A, STALL=0x1E, NYET=0x96', desc: 'ACK(0010):正确接收。NAK(1010):暂时忙。STALL(1110):端点停用。NYET(0110,HS):FIFO满了', color: 'sync-pid' },
      { name: 'EOP',      bits: 3, val: 'SE0+J', desc: '包结束信号。Handshake包是USB总线上最短的包(仅19bit), 无DATA无CRC', color: 'eop' },
    ]
  },
];

// TXN_COLORS — 事务类型 → CSS class 映射（从旧文件复制）
var TXN_COLORS = {
  sof:       'txn-sof',
  control:   'txn-control',
  interrupt: 'txn-interrupt',
  bulk:      'txn-bulk',
  isoch:     'txn-isoch',
  nak:       'txn-nak',
};

// TXN_COLOR_VARS — 事务类型 → CSS 变量映射（从旧文件复制，供 detail 面板内联样式使用）
var TXN_COLOR_VARS = {
  sof:       'var(--txn-sof)',
  control:   'var(--txn-control)',
  interrupt: 'var(--txn-interrupt)',
  bulk:      'var(--txn-bulk)',
  isoch:     'var(--txn-isoch)',
  nak:       'var(--txn-nak)',
};

// FRAME_TRANSACTIONS — 12 个时间线事务（完整复制旧文件内容）
var FRAME_TRANSACTIONS = [
  {
    id: 'sof', label: 'SOF', device: '广播', addr: '—', type: 'sof',
    width: 3, hasData: true, transferType: 'SOF 广播',
    packets: [
      {
        name: 'SOF Token 包',
        direction: 'Host → 全体',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=0xA5', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'Frame#', bits: '11', color: 'var(--color-frame)' },
          { text: 'CRC5', bits: '5', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      }
    ],
    note: 'SOF 是广播心跳包，不含设备地址。Frame Number 每 1ms +1，用于帧同步和防 Suspend。'
  },
  {
    id: 'isoch-in-cam', label: '等时 IN', device: '摄像头', addr: '3/EP2', type: 'isoch',
    width: 21, hasData: true, transferType: '等时传输',
    packets: [
      {
        name: 'IN Token 包',
        direction: 'Host → 摄像头(3)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=IN', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'ADDR=3', bits: '7', color: 'var(--color-addr)' },
          { text: 'ENDP=2', bits: '4', color: 'var(--color-addr)' },
          { text: 'CRC5', bits: '5', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'DATA0 包（视频帧数据，≤1024 Bytes）',
        direction: '摄像头(3) → Host',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=DATA0', bits: '8', color: 'var(--color-sync-pid)' },
          { text: '视频数据', bits: '≤8192', color: 'var(--color-data)' },
          { text: 'CRC16', bits: '16', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      }
    ],
    note: '⚠️ 等时传输无握手！设备发完 DATA 不等 ACK/NAK。如果 CRC 错，Host 丢弃但不重传。实时优先，正确性可妥协。'
  },
  {
    id: 'intr-in-mouse', label: '中断 IN', device: '鼠标', addr: '1/EP1', type: 'interrupt',
    width: 5, hasData: true, transferType: '中断传输',
    packets: [
      {
        name: 'IN Token 包',
        direction: 'Host → 鼠标(1)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=IN', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'ADDR=1', bits: '7', color: 'var(--color-addr)' },
          { text: 'ENDP=1', bits: '4', color: 'var(--color-addr)' },
          { text: 'CRC5', bits: '5', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'DATA0 包（按键报告，≤8 Bytes）',
        direction: '鼠标(1) → Host',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=DATA0', bits: '8', color: 'var(--color-sync-pid)' },
          { text: '按键数据', bits: '≤64', color: 'var(--color-data)' },
          { text: 'CRC16', bits: '16', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'ACK Handshake 包',
        direction: 'Host → 鼠标(1)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=ACK', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      }
    ],
    note: 'Host 周期性地轮询鼠标（bInterval 决定间隔）。这次鼠标有按键数据，正常 DATA+ACK 流程。'
  },
  {
    id: 'ctrl-setup-udisk', label: '控制 SETUP', device: 'U盘', addr: '2/EP0', type: 'control',
    width: 5, hasData: true, transferType: '控制传输（SETUP 阶段）',
    packets: [
      {
        name: 'SETUP Token 包',
        direction: 'Host → U盘(2)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=SETUP', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'ADDR=2', bits: '7', color: 'var(--color-addr)' },
          { text: 'ENDP=0', bits: '4', color: 'var(--color-addr)' },
          { text: 'CRC5', bits: '5', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'DATA0 包（8 字节 Setup Packet = Get_Descriptor 请求）',
        direction: 'Host → U盘(2)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=DATA0', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'bmReqType+bReq+wValue+wIndex+wLength(8B)', bits: '64', color: 'var(--color-data)' },
          { text: 'CRC16', bits: '16', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'ACK Handshake 包',
        direction: 'U盘(2) → Host',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=ACK', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      }
    ],
    note: '⚠️ SETUP 阶段设备必须 ACK，不能 NAK。EP0 硬件有独立 SETUP 缓冲保证永远能接收。Data Toggle 被强制复位为 DATA0。'
  },
  {
    id: 'ctrl-in-udisk', label: '控制 IN', device: 'U盘', addr: '2/EP0', type: 'control',
    width: 7, hasData: true, transferType: '控制传输（DATA 阶段）',
    packets: [
      {
        name: 'IN Token 包',
        direction: 'Host → U盘(2)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=IN', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'ADDR=2', bits: '7', color: 'var(--color-addr)' },
          { text: 'ENDP=0', bits: '4', color: 'var(--color-addr)' },
          { text: 'CRC5', bits: '5', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'DATA1 包（18 字节 Device Descriptor）',
        direction: 'U盘(2) → Host',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=DATA1', bits: '8', color: 'var(--color-sync-pid)' },
          { text: '描述符数据', bits: '144', color: 'var(--color-data)' },
          { text: 'CRC16', bits: '16', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'ACK Handshake 包',
        direction: 'Host → U盘(2)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=ACK', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      }
    ],
    note: 'DATA 阶段用 DATA1（SETUP 后第一个 DATA 阶段翻转）。Data Toggle: SETUP=DATA0, 第一个 IN=DATA1, 交替。'
  },
  {
    id: 'ctrl-out-udisk', label: '控制 OUT', device: 'U盘', addr: '2/EP0', type: 'control',
    width: 4, hasData: true, transferType: '控制传输（STATUS 阶段）',
    packets: [
      {
        name: 'OUT Token 包',
        direction: 'Host → U盘(2)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=OUT', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'ADDR=2', bits: '7', color: 'var(--color-addr)' },
          { text: 'ENDP=0', bits: '4', color: 'var(--color-addr)' },
          { text: 'CRC5', bits: '5', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'DATA1 包（0 长度 = ZLP）',
        direction: 'Host → U盘(2)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=DATA1', bits: '8', color: 'var(--color-sync-pid)' },
          { text: '(空)', bits: '0', color: 'var(--color-data)' },
          { text: 'CRC16', bits: '16', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'ACK Handshake 包',
        direction: 'U盘(2) → Host',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=ACK', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      }
    ],
    note: 'STATUS 阶段方向与 DATA 相反。DATA 是 IN（设备发数据），STATUS 就是 OUT（Host 确认）。0 长度 DATA 包 = Zero-Length Packet (ZLP)。'
  },
  {
    id: 'ctrl-setup-cam', label: '控制 SETUP', device: '摄像头', addr: '3/EP0', type: 'control',
    width: 5, hasData: true, transferType: '控制传输（SETUP 阶段）',
    packets: [
      {
        name: 'SETUP Token 包',
        direction: 'Host → 摄像头(3)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=SETUP', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'ADDR=3', bits: '7', color: 'var(--color-addr)' },
          { text: 'ENDP=0', bits: '4', color: 'var(--color-addr)' },
          { text: 'CRC5', bits: '5', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'DATA0 包（8 字节 Setup Packet = 设置亮度）',
        direction: 'Host → 摄像头(3)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=DATA0', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'bmReqType+bReq+wValue+wIndex+wLength(8B)', bits: '64', color: 'var(--color-data)' },
          { text: 'CRC16', bits: '16', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'ACK Handshake 包',
        direction: '摄像头(3) → Host',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=ACK', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      }
    ],
    note: '摄像头虽然主要用等时传输，但 EP0 控制传输仍然存在——用来做亮度、对比度等参数配置。'
  },
  {
    id: 'ctrl-in-cam', label: '控制 IN', device: '摄像头', addr: '3/EP0', type: 'control',
    width: 5, hasData: true, transferType: '控制传输（DATA 阶段）',
    packets: [
      {
        name: 'IN Token 包',
        direction: 'Host → 摄像头(3)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=IN', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'ADDR=3', bits: '7', color: 'var(--color-addr)' },
          { text: 'ENDP=0', bits: '4', color: 'var(--color-addr)' },
          { text: 'CRC5', bits: '5', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'DATA1 包（读回当前亮度值）',
        direction: '摄像头(3) → Host',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=DATA1', bits: '8', color: 'var(--color-sync-pid)' },
          { text: '亮度数据', bits: '≤16', color: 'var(--color-data)' },
          { text: 'CRC16', bits: '16', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'ACK Handshake 包',
        direction: 'Host → 摄像头(3)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=ACK', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      }
    ],
    note: '读回亮度属于控制传输的 DATA(IN) 阶段，用 DATA1 包。方向是 Device→Host（IN）。'
  },
  {
    id: 'ctrl-out-cam', label: '控制 OUT', device: '摄像头', addr: '3/EP0', type: 'control',
    width: 4, hasData: true, transferType: '控制传输（STATUS 阶段）',
    packets: [
      {
        name: 'OUT Token 包',
        direction: 'Host → 摄像头(3)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=OUT', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'ADDR=3', bits: '7', color: 'var(--color-addr)' },
          { text: 'ENDP=0', bits: '4', color: 'var(--color-addr)' },
          { text: 'CRC5', bits: '5', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'DATA1 包（ZLP）',
        direction: 'Host → 摄像头(3)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=DATA1', bits: '8', color: 'var(--color-sync-pid)' },
          { text: '(空)', bits: '0', color: 'var(--color-data)' },
          { text: 'CRC16', bits: '16', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'ACK Handshake 包',
        direction: '摄像头(3) → Host',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=ACK', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      }
    ],
    note: 'STATUS 阶段：因为 DATA 是 IN（读亮度），STATUS 就是 OUT（Host 发 ZLP 确认收到）。方向永远与 DATA 阶段相反。'
  },
  {
    id: 'bulk-out-udisk', label: '批量 OUT', device: 'U盘', addr: '2/EP2', type: 'bulk',
    width: 21, hasData: true, transferType: '批量传输',
    packets: [
      {
        name: 'OUT Token 包',
        direction: 'Host → U盘(2)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=OUT', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'ADDR=2', bits: '7', color: 'var(--color-addr)' },
          { text: 'ENDP=2', bits: '4', color: 'var(--color-addr)' },
          { text: 'CRC5', bits: '5', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'DATA0 包（512 字节文件数据）',
        direction: 'Host → U盘(2)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=DATA0', bits: '8', color: 'var(--color-sync-pid)' },
          { text: '文件数据(512B)', bits: '4096', color: 'var(--color-data)' },
          { text: 'CRC16', bits: '16', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'ACK Handshake 包',
        direction: 'U盘(2) → Host',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=ACK', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      }
    ],
    note: '批量传输"吃剩饭"——用等时和中断之后的剩余带宽。512B 是 FS 最大批量包。HS 最大 512B 亦同。DATA0/DATA1 Toggle 在每次成功 ACK 后翻转。'
  },
  {
    id: 'intr-in-nak', label: '中断 IN', device: '鼠标', addr: '1/EP1', type: 'nak',
    width: 2, hasData: false, transferType: '中断传输（无数据）',
    packets: [
      {
        name: 'IN Token 包',
        direction: 'Host → 鼠标(1)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=IN', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'ADDR=1', bits: '7', color: 'var(--color-addr)' },
          { text: 'ENDP=1', bits: '4', color: 'var(--color-addr)' },
          { text: 'CRC5', bits: '5', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'NAK Handshake 包',
        direction: '鼠标(1) → Host',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=NAK', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      }
    ],
    note: '❌ 无数据情况：Host 又一次轮询鼠标，但这次没有新按键。鼠标回 NAK——"我收到了，但没有新数据"。Token + NAK，总线上只走了 54 bits（最短事务之一）。'
  },
  {
    id: 'bulk-in-nak', label: '批量 IN', device: 'U盘', addr: '2/EP1', type: 'nak',
    width: 2, hasData: false, transferType: '批量传输（无数据）',
    packets: [
      {
        name: 'IN Token 包',
        direction: 'Host → U盘(2)',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=IN', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'ADDR=2', bits: '7', color: 'var(--color-addr)' },
          { text: 'ENDP=1', bits: '4', color: 'var(--color-addr)' },
          { text: 'CRC5', bits: '5', color: 'var(--color-crc)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      },
      {
        name: 'NAK Handshake 包',
        direction: 'U盘(2) → Host',
        flow: [
          { text: 'SYNC', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'PID=NAK', bits: '8', color: 'var(--color-sync-pid)' },
          { text: 'EOP', bits: '3', color: 'var(--color-eop)' },
        ]
      }
    ],
    note: '❌ 无数据情况：Host 想从 U 盘读数据，但 U 盘固件还没准备好。回 NAK——"暂时没数据，一会再问"。Host 稍后会重试此事务。批量传输被 NAK 可以无限重试（直到超时或 Host 放弃）。'
  }
];


// ===== 2. RENDERERS =====

var PacketRenderer = {
    /**
     * 渲染单个包结构图。
     * @param {Object} data — PACKET_DATA 元素
     *    data.id   : string — 目标容器元素 ID
     *    data.title: string — 图表标题（渲染到 .packet-title 元素中，由 HTML 预置）
     *    data.fields: Array<{name, bits, val, desc, color, flexFactor?}>
     */
    render: function(data) {
        var container = document.getElementById(data.id);
        if (!container) return;

        var totalBits = data.fields.reduce(function(sum, f) {
            return sum + (f.flexFactor || f.bits);
        }, 0);

        var diagram = document.createElement('div');
        diagram.className = 'packet-diagram';

        data.fields.forEach(function(field) {
            var widthBits = field.flexFactor || field.bits;
            var flexGrow = widthBits;

            var div = document.createElement('div');
            div.className = 'field ' + (PACKET_COLORS[field.color] || 'color-sync-pid');
            div.style.flexGrow = flexGrow;
            div.style.flexBasis = (widthBits / totalBits * 100) + '%';
            div.setAttribute('aria-label', field.name + ', ' + field.bits + ' bits, ' + field.val);

            // 多行 tooltip（相对于旧版的单行升级）
            var tooltipHtml = '<span class="tooltip">' +
                '<strong>' + field.name + '</strong>  ' + field.bits + ' bits<br>' +
                field.val + '<br>' +
                field.desc +
                '</span>';

            div.innerHTML =
                '<span class="fname">' + field.name + '</span>' +
                '<span class="fbits">' + (field.bits === 0 ? '0~8192' : field.bits + ' bit') + '</span>' +
                '<span class="fval">' + field.val + '</span>' +
                tooltipHtml;

            diagram.appendChild(div);
        });

        container.innerHTML = '';
        container.appendChild(diagram);
    },

    renderAll: function() {
        PACKET_DATA.forEach(function(data) { PacketRenderer.render(data); });
    }
};

var TimelineRenderer = {
    activeTxnBlock: null,

    render: function(txn) {
        var block = document.createElement('div');
        block.className = 'txn-block ' + (TXN_COLORS[txn.type] || 'txn-sof');
        block.style.flexGrow = txn.width;
        block.setAttribute('tabindex', '0');
        block.setAttribute('role', 'button');
        block.setAttribute('aria-expanded', 'false');
        block.title = '点击查看 ' + txn.label + ' 内部包细节';

        var dataIndicator = txn.hasData ? '' : ' ❌';
        block.innerHTML =
            '<span class="txn-device">' + txn.device + ' (Addr' + txn.addr + ')</span>' +
            '<span class="txn-label">' + txn.label + dataIndicator + '</span>' +
            '<span class="txn-type">' + txn.transferType + '</span>' +
            '<span class="txn-hint">🔍 点击展开</span>';

        var self = this;
        block.addEventListener('click', function() { self.showDetail(txn, block); });
        block.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                self.showDetail(txn, block);
            }
        });

        return block;
    },

    renderAll: function() {
        var container = document.getElementById('frameTimeline');
        if (!container) return;

        var totalWidth = FRAME_TRANSACTIONS.reduce(function(s, t) { return s + t.width; }, 0);

        var self = this;
        FRAME_TRANSACTIONS.forEach(function(txn) {
            var block = self.render(txn);
            block.style.flexBasis = (txn.width / totalWidth * 100) + '%';
            container.appendChild(block);
        });
    },

    showDetail: function(txn, block) {
        var detail = document.getElementById('txnDetail');
        var title = document.getElementById('txnDetailTitle');
        var body = document.getElementById('txnDetailBody');
        var closeBtn = document.getElementById('txnDetailClose');

        if (!detail || !title || !body) return;

        // 更新 active 状态
        if (this.activeTxnBlock) {
            this.activeTxnBlock.setAttribute('aria-expanded', 'false');
            this.activeTxnBlock.style.boxShadow = '';
        }
        this.activeTxnBlock = block;
        block.setAttribute('aria-expanded', 'true');
        block.style.boxShadow = '0 0 0 3px ' + TXN_COLOR_VARS[txn.type];

        // 填充数据
        var dataBadge = txn.hasData
            ? '<span style="color:var(--txn-isoch);font-size:12px;">✅ 有数据</span>'
            : '<span style="color:var(--txn-nak);font-size:12px;">❌ 无数据（NAK）</span>';

        title.innerHTML = txn.device + ' → ' + txn.label + ' (' + txn.transferType + ') ' + dataBadge;

        var html = '';
        txn.packets.forEach(function(pkt, i) {
            html += '<div class="txn-packet-item">';
            html += '<div class="pkt-name">' + (i === 0 ? '▶ ' : '↑ ') + pkt.name +
                    ' <span style="font-size:11px;color:var(--text-muted);">' + pkt.direction + '</span></div>';
            html += '<div class="txn-packet-flow">';
            pkt.flow.forEach(function(seg, j) {
                html += (j > 0 ? '<span class="pkt-arrow">▸</span>' : '');
                html += '<span class="pkt-bit" style="background:' + seg.color + ';" title="' + seg.bits + ' bits">' +
                        seg.text + ' (' + seg.bits + 'b)</span>';
            });
            html += '</div></div>';
        });

        if (txn.note) {
            html += '<div class="txn-note">💡 ' + txn.note + '</div>';
        }

        body.innerHTML = html;
        detail.style.display = 'block';

        var self = this;
        closeBtn.onclick = function() { self.closeDetail(); };
    },

    closeDetail: function() {
        var detail = document.getElementById('txnDetail');
        if (!detail) return;
        detail.style.display = 'none';
        if (this.activeTxnBlock) {
            this.activeTxnBlock.setAttribute('aria-expanded', 'false');
            this.activeTxnBlock.style.boxShadow = '';
            this.activeTxnBlock = null;
        }
    }
};

// ===== 3. INTERACTION =====

var ThemeManager = {
    STORAGE_KEY: 'usb-notes-theme',

    init: function() {
        // CSS :root 默认暗色；若 localStorage 存了 'light'，切到亮色
        var saved = localStorage.getItem(this.STORAGE_KEY);
        var html = document.documentElement;

        if (saved === 'light') {
            html.classList.add('light');
            html.classList.remove('dark');
        } else {
            // 默认暗色（localStorage 无记录 或 存了 'dark'）
            html.classList.add('dark');
            html.classList.remove('light');
        }

        this._updateButton();
        this._bind();
    },

    toggle: function() {
        var html = document.documentElement;
        if (html.classList.contains('dark')) {
            html.classList.replace('dark', 'light');
            localStorage.setItem(this.STORAGE_KEY, 'light');
        } else {
            html.classList.replace('light', 'dark');
            localStorage.setItem(this.STORAGE_KEY, 'dark');
        }
        this._updateButton();
    },

    _updateButton: function() {
        var btn = document.getElementById('themeToggle');
        if (!btn) return;
        var isDark = document.documentElement.classList.contains('dark');
        btn.textContent = isDark ? '\u{1F319}' : '\u{2600}';  // 🌙 / ☀
        btn.setAttribute('aria-label', isDark ? '切换到亮色模式' : '切换到暗色模式');
    },

    _bind: function() {
        var btn = document.getElementById('themeToggle');
        var self = this;
        if (btn) {
            btn.addEventListener('click', function() { self.toggle(); });
        }
    }
};

var ScrollSpy = {
    ticking: false,

    init: function() {
        var self = this;
        window.addEventListener('scroll', function() {
            if (!self.ticking) {
                requestAnimationFrame(function() { self._update(); self.ticking = false; });
                self.ticking = true;
            }
        }, { passive: true });
    },

    _update: function() {
        var cards = document.querySelectorAll('.card[id]');
        var links = document.querySelectorAll('.sidebar .sub-item');
        var current = null;

        cards.forEach(function(card) {
            var rect = card.getBoundingClientRect();
            if (rect.top <= 150) current = card.id;
        });

        links.forEach(function(link) {
            var href = link.getAttribute('href');
            var isActive = href === '#' + current;
            link.classList.toggle('active', isActive);

            // 高亮所属 Phase 的 summary
            if (isActive) {
                var details = link.closest('details');
                if (details) {
                    // 取消所有 summary 高亮
                    document.querySelectorAll('.sidebar details > summary').forEach(function(s) {
                        s.style.fontWeight = '';
                        s.style.color = '';
                    });
                    var summary = details.querySelector('summary');
                    if (summary) {
                        summary.style.fontWeight = '700';
                        summary.style.color = 'var(--accent)';
                    }
                }
            }
        });
    }
};

var SearchFilter = {
    init: function() {
        var input = document.getElementById('sidebarSearch');
        if (!input) return;

        var self = this;
        input.addEventListener('input', function() {
            self.filter(this.value);
        });

        input.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') { this.value = ''; self.filter(''); }
        });
    },

    filter: function(query) {
        var q = query.toLowerCase().trim();
        var items = document.querySelectorAll('.sidebar .sub-item');
        var detailsList = document.querySelectorAll('.sidebar details');

        items.forEach(function(item) {
            var text = item.textContent.toLowerCase();
            item.style.display = (!q || text.indexOf(q) !== -1) ? '' : 'none';
        });

        // 若 Phase 下所有子项隐藏，隐藏整个 Phase
        detailsList.forEach(function(details) {
            var visibleItems = details.querySelectorAll('.sub-item[style*="display: none"]');
            var allItems = details.querySelectorAll('.sub-item');
            if (allItems.length > 0 && visibleItems.length === allItems.length) {
                details.style.display = 'none';
            } else {
                details.style.display = '';
            }
        });
    }
};

var NavOverlay = {
    init: function() {
        var btn = document.getElementById('mobileNavBtn');
        var overlay = document.getElementById('sidebarOverlay');
        var backdrop = overlay ? overlay.querySelector('.sidebar-overlay-backdrop') : null;

        if (!btn || !overlay) return;

        var self = this;
        btn.addEventListener('click', function() { self.open(); });
        if (backdrop) {
            backdrop.addEventListener('click', function() { self.close(); });
        }

        // Escape 关闭
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && overlay.classList.contains('open')) {
                self.close();
            }
        });
    },

    open: function() {
        var overlay = document.getElementById('sidebarOverlay');
        if (overlay) overlay.classList.add('open');
    },

    close: function() {
        var overlay = document.getElementById('sidebarOverlay');
        if (overlay) overlay.classList.remove('open');
    }
};

// ===== Scroll to Top =====
function initScrollTop() {
    var btn = document.getElementById('scrollTopBtn');
    if (!btn) return;

    window.addEventListener('scroll', function() {
        var scrolled = window.scrollY > 400;
        btn.classList.toggle('visible', scrolled);
    }, { passive: true });

    btn.addEventListener('click', function() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// ===== 4. INIT =====
document.addEventListener('DOMContentLoaded', function() {
    ThemeManager.init();
    ScrollSpy.init();
    SearchFilter.init();
    NavOverlay.init();
    initScrollTop();
    PacketRenderer.renderAll();
    TimelineRenderer.renderAll();
});
