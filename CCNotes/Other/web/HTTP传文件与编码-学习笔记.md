# HTTP 传文件 · 表单 / 二进制 / base64 系统性笔记

> 整理自一次问答串：从「HTTP 报文体为什么是 `{}`」一路问到「base64 原理」与「JS 为什么难解析表单」。
> 配套交互演示见同目录 `HTTP传文件-交互演示.html`（双击用浏览器打开，可点击操作）。

---

## 目录

1. [先建心智模型：HTTP 报文结构](#1-先建心智模型http-报文结构)
2. [「表单」和「二进制」不在同一维度](#2-表单和二进制不在同一维度)
3. 传文件的四种方式
4. [响应报文 `{}` 里能直接带文件吗](#4-响应报文-里能直接带文件吗)
5. [Content-Type：浏览器怎么知道该怎么处理](#5-content-type浏览器怎么知道该怎么处理)
6. [base64 详解：二进制 → 安全文本](#6-base64-详解二进制--安全文本)
7. [「编码」的两个层次：别再混淆](#7-编码的两个层次别再混淆)
8. [为什么必须 base64：二进制被文本协议「误伤」的例子](#8-为什么必须-base64二进制被文本协议误伤的例子)
9. [为什么说 JS 难解析表单](#9-为什么说-js-难解析表单)
10. 全景速查与面试要点

---

## 1. 先建心智模型：HTTP 报文结构

任何 HTTP 请求/响应都是四段：

```
┌─────────────────────────────────────────────┐
│ 起始行   POST /upload HTTP/1.1               │
├─────────────────────────────────────────────┤
│ 头部     Content-Type: multipart/form-data   │
│          Content-Length: 1024                │
├─────────────────────────────────────────────┤
│ 空行     （头部与消息体的分割标记）             │
├─────────────────────────────────────────────┤
│ 消息体   ← 文件数据在这里（一段不透明的字节流） │
└─────────────────────────────────────────────┘
```

核心认知：**headers 是文本、结构化、一行一个键值对；body 是「一段不透明的字节流」**。HTTP 协议本身不解析 body 的内容——body 里到底放什么、怎么放，由 `Content-Type` 这一个 header 约定。

> 理解 `Content-Type` 的比喻：包裹面单上写的「里面装的是什么、该怎么拆」。

---

## 2. 「表单」和「二进制」不在同一维度

这是最初混淆的根源——它们描述的不是同一件事：

- **「二进制」** 描述的是 body 的**承载形态**：body 就是文件原始字节，没有额外结构。
- **「表单」** 描述的是 body 的**结构方式**：body 被组织成一组「字段」。

关键澄清：`multipart/form-data`（一种表单格式）**完全可以装二进制文件**。所以正确的心智是：

> 有若干种 `Content-Type`，它们是「如何排列 body 字节」的约定；多部分表单只是其中一种。

---

## 3. 传文件的四种方式

| 维度 | x-www-form-urlencoded | multipart/form-data | 原始二进制 octet-stream | JSON + base64 |
|---|---|---|---|---|
| 浏览器默认用途 | 普通文本表单 | 含文件的表单 | 手动 fetch 构造 | 手动构造 |
| body 形态 | `a=1&b=2` 文本 | 多段，boundary 分隔 | 就是文件本身字节 | 文本 JSON |
| 能否带文件 | 勉强（极低效） | 原生支持 | 就是文件 | 编码后支持 |
| 文件 + 字段混合 | 差 | 好 | 差 | 好 |
| 体积开销 | 大 | 小 | 零 | +33% |
| 能否流式 | 否 | 是 | 是 | 否 |
| 典型场景 | 登录、搜索 | 上传带元数据的文件 | 大文件直传 / PUT | 小文件内联 |

### 3.1 x-www-form-urlencoded

```
POST /login HTTP/1.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 29

username=tom&password=123
```

`key=value` 用 `&` 连接，空格变 `+`，非 ASCII 先 UTF-8 再百分号编码。纯文本格式，文件放进来要先编码成文本 → 严重膨胀 → 实践中没人用它传文件。

### 3.2 multipart/form-data（「表单」的真身）

含 `<input type="file">` 的表单，浏览器一定用它。body 被 `boundary` 切成多段：

```
POST /upload HTTP/1.1
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWx

------WebKitFormBoundary7MA4YWx
Content-Disposition: form-data; name="title"

我的照片
------WebKitFormBoundary7MA4YWx
Content-Disposition: form-data; name="avatar"; filename="a.png"
Content-Type: image/png

<这里直接是 PNG 的原始二进制字节>
------WebKitFormBoundary7MA4YWx--
```

三个要点：

1. **每段自带 headers**：`name` 是字段名，文件名放 `filename`，MIME 放各段 `Content-Type`。这就是它能同时传「文件 + 多个文本字段」的原因。
2. **文件段里是原始二进制**，无编码，体积几乎无开销。
3. **约定**：每段前是 `--boundary`，最后一段是 `--boundary--`。

### 3.3 原始二进制

只传一个文件、不需要字段结构时：

```
PUT /files/report.pdf HTTP/1.1
Content-Type: application/pdf
Content-Disposition: attachment; filename="report.pdf"
Content-Length: 102400

<PDF 的原始字节>
```

最省流量，服务端拿到就是可写盘的流。代价：**没法在一个请求里再带别的字段**。

### 3.4 选型决策

```
要发一个文件
 ├─ 要同时带多个字段？ ── 是 ──> multipart/form-data
 └─ 否
     ├─ 文件小 / 要嵌进 JSON？ ── 是 ──> JSON 里 base64
     └─ 否（大 / 要流式） ─────> raw binary (application/octet-stream)
```

---

## 4. 响应报文 `{}` 里能直接带文件吗

先答「`{}` 是什么格式」：`{}` 是 **JSON 的对象语法**，格式就是 **JSON**，由 `Content-Type: application/json` 标定（RFC 8259）。

要分清两层：

- **传输格式**：JSON（通用标准，不用公司去定）。
- **业务协议**：`{}` 里放哪些字段、什么含义——这才是公司「定协议」定的东西。

### 公司常见的「统一响应信封」

```json
{ "code": 0, "message": "success", "data": { "id": 1, "name": "tom" } }
```

- `code`：**业务状态码**（和 HTTP 状态码是两码事）。
- `message` / `msg`：给人看的提示。
- `data` / `result` / `payload`：真正的业务数据。

字段名各家不同——这正是每家公司协议文档要写清的部分。别混淆的两种「同名形状」：

| 结构特征 | 实际格式 |
|---|---|
| `{"jsonrpc":"2.0","id":1,"result":...}` | JSON-RPC 2.0 |
| `{"data":{...},"errors":[...]}` | GraphQL 响应 |
| `{"code":0,"message":"","data":{}}` | 公司自定义统一信封 |

### 文件能不能放进 `{}`

**技术上能，但必须先编码；大文件几乎从不这么做。** 根因：JSON 是 UTF-8 文本格式，文件字节是任意二进制——**无法用 JSON 字符串合法表示**。想放就得先 base64。

| 文件大小/场景 | 推荐 |
|---|---|
| 小（几 KB ~ 100KB）、要一次原子返回 | base64 内联 |
| 大、媒体、需缓存/CDN/断点续传 | JSON 返回下载 URL（最好预签名） |
| 需要边下边用 | 只能 URL 或 raw binary，不能 base64 |

一句话：**JSON 适合放「关于文件的信息」，不适合放「文件本身」。**

---

## 5. Content-Type：浏览器怎么知道该怎么处理

精确结论：**Content-Type 是浏览器决定「如何处理 body」的首要依据，但它是「提示」，不是「强制」——按场景决定听不听，有时还会反过来自己猜。**

### 关键点：HTTP 协议本身不解析 body

传输层只把 body 当不透明字节流，真正做「解析并处置」的是应用层（浏览器引擎 / 服务端框架）。

### 分场景

| 场景 | 消费方 | Content-Type 的作用 | 会不会被忽略 |
|---|---|---|---|
| 顶层导航（地址栏） | 浏览器渲染引擎 | 选处理器：`text/html`→渲染、`image/*`→显示、`application/pdf`→PDF 阅读器、`application/octet-stream`→下载 | 缺失/错误时 **MIME 嗅探**自己猜 |
| 子资源 `<img>/<script>/<link>` | 加载器 | **类型校验**：`<script type="module">` 类型不符直接拒绝 | 图片宽松（嗅探），script/CSS 严格 |
| `fetch` / `XHR` | **你的 JS 代码** | **只是元信息**，浏览器不自动解析 | 完全不自动解析 |
| 表单提交 | 服务端 | 决定服务端怎么解析 | 服务端按它选 parser |

### 最容易误解的一点：`fetch` 不根据 Content-Type 自动解析

```js
const res = await fetch('/api/user');
// res.body 是字节流，res 不是对象
const obj = await res.json();   // ← 这一步是你手动调的
```

两个反证：

- Content-Type 是 `application/json`，你**不调** `res.json()`，它永远不会变对象。
- Content-Type 是 `text/plain`，你**照样可以**调 `res.json()`，解析失败才抛错。

### MIME 嗅探与安全

Content-Type 缺失/模糊/不可信时，浏览器会**读前几个字节猜类型**。经典攻击：

> 上传内容为 `<script>...</script>` 的文件，服务器返回 `Content-Type: text/plain`。无防护时浏览器嗅探到「像 HTML」→ 按 HTML 渲染 → **脚本执行 → XSS**。

防御：`X-Content-Type-Options: nosniff`——禁止浏览器违反声明的类型去嗅探。

> 所以严格说：**Content-Type 是「建议类型」，`nosniff` 才把它钉成「强制类型」。**

### charset 优先级

`Content-Type: text/html; charset=utf-8` 里的 charset 只是其中之一。HTML 的编码判定优先级：**BOM > HTTP 头 charset > `<meta charset>`**。这也是「header 写了 utf-8 却还乱码」的常见原因。JSON 规定必须 UTF-8，所以 `application/json` 不再需要 charset。

---

## 6. base64 详解：二进制 → 安全文本

**base64 是编码（encoding），不是加密，也不是压缩。** 把任意字节重新表示为纯 ASCII 文本；原文一比特不丢，可完整还原。

### 为什么需要它

很多传输通道是**面向文本**的：SMTP 只稳妥传可打印 ASCII；URL / JSON / XML / HTML 里某些字节是保留字符。要在文本通道里塞二进制，就得先「化妆」成一串无害的可打印字符。

### 核心机制：6 比特一组

关键数字 **64 = 2⁶**，即一个字符承载 6 比特。

1. 把原始字节看成一长串比特；
2. 每 **6 比特**切一组；
3. 每组查 64 字符表，换成对应字符。

一个字节 8 比特，6 与 8 的最小公倍数是 24：**3 字节（24 比特）= 4 个 6 比特组 = 4 个字符**。这就是 3:4 比例、膨胀 **4/3 ≈ 133%（+33%）** 的来源。

### 亲手走一遍：`Man` → `TWFu`

```
M       a       n
01001101 01100001 01101110      ← 3 字节 = 24 比特

按 6 比特重切：
010011  010110  000101  101110
  19      22       5      46

查表 → T  W  F  u
```

验证（浏览器 Console）：

```js
btoa("Man")   // "TWFu"
atob("TWFu")  // "Man"
```

### 64 字符表

| 索引 | 字符 |
|---|---|
| 0–25 | `A`–`Z` |
| 26–51 | `a`–`z` |
| 52–61 | `0`–`9` |
| 62 | `+` |
| 63 | `/` |

选这 64 个，正因它们在**任何文本通道里都安全**（无控制字符、无引号、无换行）。

### `=` 填充

字节数不是 3 的倍数时，最后一组补 0，末尾补 `=` 表示「缺多少字节」：

```
"Ma"  (2 字节) → TWE=     （末尾 1 个 =）
"M"   (1 字节) → TQ==     （末尾 2 个 =）
"Man" (3 字节) → TWFu     （无 =）
```

`=` 只携带「原始数据有多少字节」的信息，不含内容。JWT 常去掉它。

### 容易搞混的点

- **不是加密**：公开算法、任何人可瞬间还原。JWT 中间段 base64 直接 decode 就是明文 payload。
- **对比 hex**：hex 每字节 2 字符、膨胀 100%；base64 膨胀 33%，更省空间，可读性差些。
- **base64url 变体**：`+`→`-`、`/`→`_`，因为 `+` `/` 在 URL 里有特殊含义。JWT 用的就是它。**两种表混用会解错。**
- **不能变小**：无损编码不可能普遍压缩，一定膨胀 33%。

### 接收/发送时的实际成本

**接收（服务端返回 base64）：**

```js
const obj = await res.json();          // 外层 JSON 轻松解析 ✅
const bin = atob(obj.content);         // 但这是个 base64 字符串 😕
const bytes = Uint8Array.from(bin, c => c.charCodeAt(0));
const blob = new Blob([bytes], { type: obj.mimeType });  // 手动拼回文件
```

**发送（前端上传文件）：**

```js
const buf = await file.arrayBuffer();                  // 读成字节
const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));  // 手动 base64
const body = JSON.stringify({ name: file.name, content: b64 });
```

对比 `FormData` 的 `fd.append('avatar', file)` 一行——这就是「表单传文件更省事」的真实含义。

---

## 7. 「编码」的两个层次：别再混淆

疑问：「JSON 传的是 base64 吗？可我看到的就是 ASCII 呀！」

根源是 **「编码」被用在两个不同层次**：

```
HTTP body 原始字节
   │
   │  ①字符编码层：字节 ↔ 文本          ← JSON 规定用 UTF-8（ASCII 是其子集）
   ▼
JSON 文本  { "name": "tom", "content": "iVBORw0..." }
                                     └────────────┘
   │  ②内容编码层：二进制 ↔ 安全文本     ← 只有承载二进制时才有 base64
   ▼
```

| | ①字符编码 | ②内容编码 |
|---|---|---|
| 例子 | ASCII、UTF-8、GBK | base64、quoted-printable |
| 变换方向 | 字符 ↔ 字节 | 字节 ↔ 安全文本 |
| 谁规定 | 文本协议规范 | 你的数据是否含二进制 |
| 何时出现 | 只要传文本就永远存在 | 按需，传二进制时才用 |
| 输出字符集 | 可能含任意 Unicode | 只含 64 个 ASCII 安全字符 |

**「JSON 是 ASCII/UTF-8」说的是①；「JSON 里某字段用了 base64」说的是②。两层可叠加，不冲突。**

要点：**不是所有 JSON 都用 base64**。`{"name":"tom"}` 里的值本身就是文本，无需 base64。只有往 JSON 里塞二进制时才出现。

**判断某字段是不是 base64**：字段名暗示（`content`/`file`/`data`/`bytes`）、值长且只含 `A–Z a–z 0–9 + /`、长度为 4 的倍数、末尾可能有 `=`；或出现在 `data:image/png;base64,...` 这种 data URI 里。

---

## 8. 为什么必须 base64：二进制被文本协议「误伤」的例子

这是 base64 存在的根本理由。分两种性质，第二种最危险。

### ① 结构性误伤（报错 / 被解析错，容易发现）

- **NUL 空字节 `0x00`**：C 系函数以 `\0` 结尾。文件名 `shell.php\0.jpg` → 扩展名校验看到 `.jpg` 放行，真正落盘/执行时被 `\0` 截断成 `shell.php`——典型的截断绕过。
- **CRLF（`0x0D 0x0A`）**：HTTP 头 / 邮件头 / multipart 都靠换行分帧。文件名里塞 `a.txt\r\nX-Injected: evil` → 接收方把后半段当成**新的一行头部**——「头注入 / HTTP response splitting」。
- **双引号 `0x22`**：multipart 的 `filename="a.png"` 是带引号的结构化字段。文件名含 `"` 会提前闭合属性，注入出额外参数。

### ② 语义性误伤（不报错，但数据被悄悄改坏，最难查）

- **非法 UTF-8 字节**：JSON 规范要求 UTF-8 文本。把 JPEG/PNG 字节**直接当字符串**塞进去，非法字节会被解码器替换成 `U+FFFD`（`�`）。再编码回字节时**和原字节对不上——数据不可逆损坏**。它不报错，只是静默改变数据。

> 这就是「必须先把二进制 base64 化」的根本原因：base64 的产物全是安全 ASCII，穿过任何文本层都不会被碰。

（这些在 `HTTP传文件-交互演示.html` 的卡片 3 里可点击复现。）

---

## 9. 为什么说 JS 难解析表单

**浏览器端其实不难，难的是 Node 服务端**——很多人把两者混着说。

### 9.1 浏览器端：现代 JS 很顺手

```js
// 发送：FormData 自动序列化成 multipart
const fd = new FormData(form);
fd.append("avatar", fileInput.files[0]);
await fetch("/upload", { method: "POST", body: fd });

// 接收：请求对象有原生解析方法
const fd2 = await request.formData();   // 拿到 FormData
const file = fd2.get("avatar");          // 拿到 File/Blob
```

历史来源：老式 `<form>` 提交是**整页导航**，它是为「无 JS 时代」设计的。早期 AJAX 要先 `preventDefault()` 拦掉默认导航再手动组数据，于是有「JS 和表单不天然契合」的说法。有了 `FormData` + `fetch` 后这个鸿沟已填平。

### 9.2 Node 服务端：真痛点

Node 原生 `http` 模块**只给你原始可读流 `req`**，不解析 body、更不认识 multipart。你得自己：

- 从 `Content-Type` 里抠出 `boundary`；
- 逐 chunk 扫描字节流，按 `\r\n--boundary` 切分；
- 解析每段自己的 headers / `filename` / `Content-Type`；
- 把文件段边收边写盘。

所以上传全靠第三方库：Express → `multer`，Koa → `@koa/multer`，纯 Node → `busboy` / `formidable` / `multiparty`。

> **「JS 天然无法解析表单」说的就是：原生能力缺失，必须依赖这些库。**

### 9.3 为什么 multipart 本身比 JSON 难解析

任何语言都如此，五条根因：

1. **非结构化流**：JSON 有明确语法与 token 边界；multipart 靠**可能出现在数据里的随机字符串**做分隔，只能逐字节扫描。
2. **二进制安全**：文件段是任意字节，不能用字符串/正则简单处理。
3. **流式要求**：大文件必须边收边写，还得处理「边界跨两个 chunk」的情况。
4. **CRLF 与转义细节**：定界是 `\r\n--boundary`，末尾有 `--`；`Content-Disposition` 的 filename 还有 RFC 5987 编码规则。
5. **每段内部又是「HTTP 头 + body」的嵌套结构**，等于要写一个小型流式状态机。

对比 JSON：文本格式、有标准 parser、`JSON.parse` 一行搞定、天然对齐 JS 数据模型。这就是「JSON 在 JS 世界零摩擦，表单传文件有摩擦」的原因。

---

## 10. 全景速查与面试要点

### 一句话串起来

```
文件 = 原始字节
  ├─ 带其他字段上传  → multipart/form-data（boundary 分隔，二进制安全）
  ├─ 只传一个文件    → raw binary（最省，但带不了字段）
  └─ 要塞进 JSON     → base64（+33%，不能流式）
```

### 速查表

| 问题 | 答案 |
|---|---|
| 响应 `{}` 是什么格式 | JSON（Content-Type: application/json） |
| JSON 里能放文件吗 | 能，但要先 base64；大文件改用下载 URL |
| Content-Type 决定浏览器怎么解析吗 | 是「首要提示」，但分场景，`fetch` 不自动解析 |
| 浏览器会无视 Content-Type 吗 | 类型缺失/模糊时会 MIME 嗅探；`nosniff` 可禁止 |
| base64 是加密吗 | 不是。公开可逆，不提供保密性 |
| base64 为什么膨胀 33% | 6 比特一字符，3 字节变 4 字符 |
| base64 为什么末尾有 `=` | 原始字节数不是 3 的倍数时补位对齐 |
| 「JSON 是 ASCII」和「JSON 用 base64」矛盾吗 | 不矛盾，分属字符编码层 / 内容编码层 |
| JSON 传文件时 JS 要做什么 | `res.json()` 后还要手动 `atob` 解码 |
| 表单传文件时呢 | `res.formData()` 直接拿 `File` 对象 |
| Node 解析 multipart 要什么 | 第三方库（multer / busboy / formidable 等） |
| 为什么必须 base64 | 二进制直接进文本层会被结构性误伤或静默损坏 |

### 面试/实战易踩坑

1. **base64 ≠ 加密**：JWT payload 直接 decode 就是明文。
2. **HTTP 状态码 ≠ 业务 code**：`200` 响应体里 `code: 1001` 也是常见「失败」。
3. **`{}` 不代表成功**：空对象、`{"code":500}` 都合法。
4. **严格 JSON**：键必须双引号、不能有注释/尾逗号/`undefined`；`{name:'tom'}` 是 JS 字面量不是 JSON。
5. **大文件别用 base64 内联**：内存爆炸 + 无法流式 + 无断点续传。
6. **`filename` 里的特殊字符要清洗**：防 CRLF / 引号注入。
7. **charset 优先级**：BOM > HTTP 头 > `<meta>`；服务端返回要让 header 和内容一致。

### 参考规范

- RFC 9110 — HTTP 语义
- RFC 7578 — `multipart/form-data`
- RFC 8259 — JSON
- RFC 4648 — Base16/32/64 编码（base64url）
- RFC 6266 / 5987 — Content-Disposition 与 filename 编码
- `X-Content-Type-Options: nosniff` — 禁止 MIME 嗅探
