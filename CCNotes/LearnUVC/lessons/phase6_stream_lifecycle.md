# Phase 6 · 流生命周期（建流 / 开闸 / 关闸 / 拆管）

> 对应主干链第 ⑥⑦⑨ 步。学完本 Phase 你会：按合同建流、启动数据传输、停止、拆除，以及"快捷组合"和"分步操作"两套 API 的选择。
> 演示程序：`../demos/phase6_stream_lifecycle.c`（需先解决 D1 才能实跑）

---

## 1. 本 Phase 接口一览

| 接口 | 作用 | 输入 | 拿到什么数据 |
|------|------|------|-------------|
| `uvc_stream_open_ctrl` | 按合同建流 | devh + 合同 | `uvc_stream_handle_t *`（水管） |
| `uvc_stream_start` | 开闸：启动数据传输 | 流句柄 + 回调(可 NULL) + user_ptr + flags | 无 |
| `uvc_stream_start_iso` | 同上（**已废弃**，直接调 start） | 同上（无 flags） | 无 |
| `uvc_stream_stop` | 关闸 | 流句柄 | 无 |
| `uvc_stream_close` | 拆管 | 流句柄 | 无 |
| `uvc_start_streaming` | **快捷组合**：建流+开闸一步 | devh + 合同 + 回调 + user_ptr + flags | 无 |
| `uvc_start_iso_streaming` | 同上（**已废弃**） | — | — |
| `uvc_stop_streaming` | 停掉该设备上**所有**流 | devh | 无 |

---

## 2. 两套 API：快捷组合 vs 分步操作

```
快捷组合（官方示例用的）:           分步操作（需要轮询/中途改参数时）:
uvc_start_streaming(devh, &ctrl,      uvc_stream_open_ctrl(devh, &strmh, &ctrl);
                    cb, ptr, 0)        uvc_stream_start(strmh, cb, ptr, 0);
uvc_stop_streaming(devh);              uvc_stream_stop(strmh);
                                       uvc_stream_close(strmh);
```

- 快捷组合内部就是 open_ctrl + start（stream.c:931，start 失败会自动 close 帮你清理）。
- **分步操作多给你一个 `strmh` 句柄**——轮询取帧（Phase 7 的 `uvc_stream_get_frame`）必须要它。
- 一个 devh 上同一流接口只能开**一条**流：重复 open_ctrl 同一接口返回 `UVC_ERROR_BUSY`。

## 3. uvc_stream_open_ctrl：铺水管

**内部流程**（stream.c:1005）：

1. 检查该流接口是否已有流（有 → BUSY）
2. **claim 流接口**（Phase 3 只 claim 了 VC 接口，VS 接口在这里才占）
3. **Commit 合同**（`uvc_stream_ctrl`，Phase 5 的"定"在这里生效）
4. 按 `dwMaxVideoFrameSize` 分配**双缓冲**（outbuf/holdbuf）+ 元数据缓冲
5. 初始化互斥锁/条件变量（帧的生产者-消费者同步用），挂进 devh->streams

**拿到什么**：`uvc_stream_handle_t *strmh`——水管。之后 start/get_frame/stop/close 都围绕它。

**注意**：建流 ≠ 开流。open_ctrl 后设备还没开始发数据，可以安全地调整参数、改回调设置。

## 4. uvc_stream_start：开闸

```c
uvc_error_t uvc_stream_start(uvc_stream_handle_t *strmh,
                             uvc_frame_callback_t *cb,
                             void *user_ptr, uint8_t flags);
```

内部做三件大事（stream.c:1075，与旧笔记阶段 7.2 对应）：

1. **决定传输模式**：VS 接口有多个 altsetting → 等时传输；只有一个 → 批量传输。（UVC 规范：VS 接口用等时传输当且仅当它有多个 altsetting。）
2. **选 altsetting**（等时时）：从低到高找第一个"每包容量 ≥ dwMaxPayloadTransferSize"的配置，切过去，然后按该端点容量创建 4 个传输缓冲（`LIBUVC_NUM_TRANSFER_BUFS`，每个挂 5 秒超时）。
3. **启动回调线程**（cb 非 NULL 时）：libuvc 内部开一个线程，每收到完整帧就调用你的 cb。

**cb 传 NULL** = 轮询模式：不开回调线程，由你自己调 `uvc_stream_get_frame` 取帧（Phase 7）。
**flags 传 0**：官方注释明确"当前未定义，必须传 0"。

**大坑（头文件原文警告）**：回调运行在 libuvc 的内部线程里，**回调期间不能调用任何 uvc_* 函数**——流控制、控制传输都不行，会死锁。转换函数（`uvc_any2rgb` 等，Phase 10）例外，它们不碰设备。回调要尽量快：慢回调会让后续帧在内部排队/丢失。

## 5. uvc_stream_stop / uvc_stream_close：关闸与拆管

**stop 的内部序列**（stream.c:1492，一个教科书级的线程同步示范）：

```
running=0 → cancel 全部传输 → 等所有传输在回调里自清理完毕
→ 唤醒并 join 回调线程 → 返回
```

cancel 之后不能立即 free 传输缓冲——异步回调可能还在用，所以等回调把它们标记释放。**stop 是阻塞的**，会等到回调线程完全退出才返回（官方示例注释：Blocks until last callback is serviced）。

**close**（stream.c:1542）：若还在跑先 stop → 释放流接口（并把 altsetting 归零）→ free 双缓冲和元数据缓冲 → 销毁锁 → free 句柄。**close 之后 strmh 作废**。

## 6. 真实运行示例

`demos/phase6_stream_lifecycle.c`（需 D1 解决后运行）：协商（640x480@30 兜底）→ open_ctrl → start（回调模式，打印前 3 帧）→ 收帧 3 秒 → stop → close。

预期输出形态：

```
找到摄像头
摄像头已打开
流已建立（合同已 commit）
流已启动，收帧 3 秒……
  收到帧 1: YUYV 640x480, 614400 字节
  收到帧 2: YUYV 640x480, 614400 字节
  收到帧 3: YUYV 640x480, 614400 字节
3 秒共收到 90 帧（约 30.0 fps）
uvc_stream_stop -> Success
流已关闭
```

验证点：帧数/3 秒 ≈ 谈判的 fps（30），说明协商→建流→传输整条链路正确。

---

## 7. 本 Phase 小结

```
合同 ──> uvc_stream_open_ctrl ──> strmh（水管，合同在此 Commit）
strmh ──> uvc_stream_start(cb, NULL, 0)
              ├─ 等时/批量自动判定（多 altsetting = 等时）
              ├─ altsetting 选择：找第一个容量够大的
              └─ cb 非 NULL 时开内部回调线程
strmh ──> uvc_stream_stop  ──> cancel+等待+join（阻塞）
strmh ──> uvc_stream_close ──> 释放接口与缓冲（句柄作废）
```

自检清单：
- [ ] 知道快捷组合与分步操作的区别，轮询取帧必须用分步
- [ ] 知道 open_ctrl 时 Commit 才真正生效
- [ ] 知道等时 vs 批量的判定规则（num_altsetting > 1）
- [ ] 知道回调线程的限制：不能调 uvc_*，要快
- [ ] 知道 stop 阻塞等回调退出，close 后句柄作废

下一步：Phase 7 帧获取——`uvc_frame_t` 逐字段精讲，轮询与回调两种吃法。
