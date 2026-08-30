# Phase 1 · 初始化与退出（uvc_init / uvc_exit + 诊断函数）

> 对应主干链第 ① ⑪ 步。学完本 Phase 你会：创建/释放 UVC 上下文，把错误码翻译成可读文字。
> 演示程序：`../demos/phase1_init.c`，真实运行输出：`../outputs/phase1_run.txt`

---

## 1. 本 Phase 接口一览

| 接口 | 作用 | 输入 | 拿到什么数据 | 返回值 |
|------|------|------|-------------|--------|
| `uvc_init` | 创建全局上下文（工作台） | `usb_ctx`（可传 NULL） | `uvc_context_t *`（输出参数） | `uvc_error_t`：`UVC_SUCCESS`(0) 或负错误码 |
| `uvc_exit` | 释放上下文及一切残留 | `uvc_context_t *` | 无 | 无（void） |
| `uvc_strerror` | 错误码 → 可读文字 | `uvc_error_t` | `const char *` 错误描述 | — |
| `uvc_perror` | 把错误打到 stderr | `uvc_error_t` + 自定义前缀 | 无（直接打印） | — |

另有 `uvc_print_diag` / `uvc_print_stream_ctrl` 两个诊断函数，它们的输入（设备句柄、流合同）要到 Phase 3/5 才拿得到，本 Phase 先认识签名，届时再演示。

---

## 2. uvc_init：领一张工作台

### 2.1 签名

```c
uvc_error_t uvc_init(uvc_context_t **pctx, struct libusb_context *usb_ctx);
```

| 参数 | 方向 | 含义 |
|------|------|------|
| `pctx` | **输出** | 传一个 `uvc_context_t*` 变量的地址（二级指针），uvc_init 把创建好的工作台指针写进去 |
| `usb_ctx` | 输入 | 传 `NULL` 表示"libuvc 自己创建一个 libusb 上下文"（99% 的情况）；传你自己的 libusb 上下文表示"共用" |

**为什么 pctx 是二级指针？** 这是 C 语言"函数返回多个值"的惯用法：函数既要返回错误码，又要返回创建的对象，就把对象通过指针参数"吐"出来。调用方这样用：

```c
uvc_context_t *ctx = NULL;          /* 先置 NULL */
uvc_error_t ret = uvc_init(&ctx, NULL);  /* 注意 &ctx */
/* 成功后 ctx 就是有效的工作台指针 */
```

### 2.2 内部做了什么（读 init.c 源码，共 3 件事）

```c
uvc_error_t uvc_init(uvc_context_t **pctx, struct libusb_context *usb_ctx) {
  uvc_context_t *ctx = calloc(1, sizeof(*ctx));   /* ① 分配并清零一个 context */

  if (usb_ctx == NULL) {
    ret = libusb_init(&ctx->usb_ctx);             /* ② 创建 libusb 上下文 */
    ctx->own_usb_ctx = 1;                          /*    标记：归我管 */
    if (ret != UVC_SUCCESS) { free(ctx); ctx = NULL; }  /* 失败就全部退回 */
  } else {
    ctx->own_usb_ctx = 0;                          /* ③ 共用：不归我管 */
    ctx->usb_ctx = usb_ctx;
  }
  if (ctx != NULL) *pctx = ctx;
  return ret;
}
```

三个要点：

1. **uvc_context_t 里包着一个 libusb_context_t**（字段叫 `usb_ctx`）。所谓"UVC 上下文"本质是 libusb 上下文 + libuvc 自己的簿记。
2. **它不碰任何设备**。此时工作台上空空如也，一个摄像头都没连接——这很正常，找设备是 Phase 2 的事。
3. **它不启动任何线程**。事件处理线程要等到 `uvc_open` 成功之后才启动（Phase 3 讲），所以 init 本身极快。

### 2.3 usb_ctx 参数什么时候传非 NULL？

只有一种场景：你的程序里**已经**在用 libusb（比如还要操作别的 USB 设备），想共用一个 libusb 上下文。代价是（源码注释明确警告）：

> 如果提供了自己的 USB context，你必须自己调用 `libusb_handle_events` 之类函数处理 libusb 事件。

**坑**：不处理事件 → libuvc 的异步传输收不到完成通知 → 摄像头"卡死"没数据。所以除非你真的懂 libusb，**永远传 NULL**。

---

## 3. uvc_exit：归还工作台

### 3.1 签名与内部流程

```c
void uvc_exit(uvc_context_t *ctx);
```

读 init.c 源码，它做 3 件事：

1. **遍历所有还开着的设备，逐个 uvc_close**——即使你忘了关设备，它也会帮你关掉（不会泄漏）。
2. 如果 libusb 上下文是 libuvc 自己创建的（`own_usb_ctx == 1`），调 `libusb_exit` 归还。
3. `free(ctx)` 释放工作台本身。

### 3.2 坑：exit 之后一切指针全部作废

源码注释原话："This function invalides any existing references to the context's cameras."（本函数使一切指向该上下文摄像头的引用失效）。

所以调用顺序是铁律：**exit 必须是最后一个 libuvc 调用**。uvc_exit 之后再碰 ctx、devh、strmh 任何一个指针都是野指针访问。

---

## 4. 错误码体系：uvc_error_t

libuvc 的几乎所有函数都返回 `uvc_error_t`。完整 16 个值（libuvc.h 定义）：

| 常量 | 值 | 含义 |
|------|----|------|
| `UVC_SUCCESS` | 0 | 成功 |
| `UVC_ERROR_IO` | -1 | 输入/输出错误 |
| `UVC_ERROR_INVALID_PARAM` | -2 | 参数无效 |
| `UVC_ERROR_ACCESS` | -3 | 拒绝访问 |
| `UVC_ERROR_NO_DEVICE` | -4 | 无此设备 |
| `UVC_ERROR_NOT_FOUND` | -5 | 未找到 |
| `UVC_ERROR_BUSY` | -6 | 忙 |
| `UVC_ERROR_TIMEOUT` | -7 | 超时 |
| `UVC_ERROR_OVERFLOW` | -8 | 溢出 |
| `UVC_ERROR_PIPE` | -9 | 管道错误 |
| `UVC_ERROR_INTERRUPTED` | -10 | 被打断 |
| `UVC_ERROR_NO_MEM` | -11 | 内存不足 |
| `UVC_ERROR_NOT_SUPPORTED` | -12 | 不支持 |
| `UVC_ERROR_INVALID_DEVICE` | -50 | 非 UVC 设备 |
| `UVC_ERROR_INVALID_MODE` | -51 | 模式不支持（协商失败） |
| `UVC_ERROR_CALLBACK_EXISTS` | -52 | 回调已存在（轮询/回调二选一） |
| `UVC_ERROR_OTHER` | -99 | 其他错误 |

**有意思的设计**：这些值和 libusb 的错误码**数值完全相同**——所以 init.c 里敢直接写 `ret = libusb_init(...)` 把 libusb 的返回值当 uvc_error_t 用。协议细节会在这套数值体系里反复出现。

现在只需记住三个最常碰到的：
- `UVC_SUCCESS` = 0（判断成功用 `ret == UVC_SUCCESS` 或 `ret >= 0`）
- `UVC_ERROR_ACCESS` = -3（Windows 上打开被系统驱动占用的设备——后面 Phase 2 就会撞上）
- `UVC_ERROR_NOT_FOUND` = -5（找不到设备/格式）

---

## 5. uvc_strerror / uvc_perror：把数字翻译成人话

### 5.1 做什么

```c
const char *uvc_strerror(uvc_error_t err);
void uvc_perror(uvc_error_t err, const char *msg);
```

- `uvc_strerror`：查表（diag.c 里 16 行对照表）返回字符串；查不到返回 `"Unknown error"`。**不打印**，只是给你一个字符串——你想怎么用都行。
- `uvc_perror`：把 `msg + ": " + 错误文字 + " (错误码)"` 打印到 **stderr**。相当于 strerror 的快捷打印版。

### 5.2 用法惯例

```c
res = uvc_open(dev, &devh);        /* 几乎所有调用都要检查返回值 */
if (res != UVC_SUCCESS) {
    uvc_perror(res, "uvc_open");   /* 打出 "uvc_open: Access denied (-3)" */
    return -1;
}
```

### 5.3 坑：stdout 与 stderr 的输出顺序会乱

stdout 经过管道（比如重定向到文件）时是**块缓冲**，stderr 是**无缓冲**。两者混用输出时，stderr 的内容经常"抢先"出现——本 Phase 真实运行输出里 `模拟一个错误` 那一行排到了最前面，就是这个原因。**调试信息用 stderr（uvc_perror 正是如此）**，正常结果用 stdout，这样重定向时不会互相污染。

---

## 6. 真实运行示例

### 6.1 演示程序

源码：`../demos/phase1_init.c`（编译与运行说明见文件头部注释）。逻辑：init → 检查返回 → 演示 strerror/perror → exit。

### 6.2 真实输出（本机 2026-08-30，MinGW gcc 8.1 + libuvc v0.0.7 + libusb 1.0.27）

```
uvc_init 返回: Success (0)
ctx 指针: 0000000000E28DC0（非 NULL 表示工作台创建成功）

-- uvc_strerror 对照表（挑几个）--
UVC_SUCCESS        =  0 -> "Success"
UVC_ERROR_ACCESS   =  -3 -> "Access denied"
UVC_ERROR_TIMEOUT  =  -7 -> "Timeout"
不存在的码 99      ->  "Unknown error"（查无此码时的兜底文字）

-- uvc_perror 输出格式（打到 stderr）--
模拟一个错误: Not found (-5)

uvc_exit 执行完毕（工作台已归还）
```

（stderr 那行实际显示在输出最前，此处按逻辑顺序摆放——就是 5.3 讲的缓冲现象。）

### 6.3 输出逐行解读

| 输出 | 说明了什么 |
|------|-----------|
| `Success (0)` | init 成功，返回码为 0 |
| `ctx 指针: 0xE28DC0` | 工作台真实分配出来了（本次运行落在内存 0xE28DC0，每次运行都不同） |
| `"Access denied"` / `"Timeout"` | strerror 查表命中 |
| `"Unknown error"` | 99 不在表中，兜底字符串 |
| `模拟一个错误: Not found (-5)` | perror 格式：前缀 + 冒号 + 文字 + 码 |
| `uvc_exit 执行完毕` | 正常退出，无报错 |

---

## 7. 本 Phase 小结

```
uvc_init ──> 工作台 ctx（包里藏着一个 libusb 上下文）
   │
   ▼ （Phase 2 起的所有操作都发生在 ctx 这张工作台上）
uvc_exit  （最后一步：帮你关掉忘记关的设备，归还一切）

检查返回值 ──> uvc_perror / uvc_strerror 把错误翻译成人话
```

自检清单：
- [ ] 能说出 uvc_init 两个参数各干什么，为什么 pctx 是二级指针
- [ ] 知道 uvc_init 内部 3 件事（calloc / libusb_init / 标记归属）
- [ ] 知道 uvc_exit 会帮你关掉忘记关的设备，且 exit 后所有指针作废
- [ ] 会查 uvc_error_t 表，认识 SUCCESS/ACCESS/NOT_FOUND 三个常用码
- [ ] 知道 stdout/stderr 缓冲差异导致的输出乱序

下一步：Phase 2 设备发现——用刚领的工作台去找摄像头。
