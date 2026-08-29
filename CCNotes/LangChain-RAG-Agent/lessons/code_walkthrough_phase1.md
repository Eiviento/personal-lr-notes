# 代码精读 1：phase1_4_req_to_protocol.py（纯 SDK 版）

> 项目的第一份脚本，也是所有后续代码的地基：不装任何框架，只用 openai 库调 DeepSeek。
> 读法：每一块按"三问"读——**干什么 / 吃什么吐什么 / 为什么这么写**。

## 数据流全景

```
命令行需求文本 → 拼进说明书(SYSTEM_PROMPT) → 调 DeepSeek API → 解析 JSON → 打印表格 + 存文件
```

## 六块详解

### 第 1 块：头部注释 + 导入 + 配置（1~27 行）

| 要素 | 要点 |
|------|------|
| 开头 `"""..."""` | 每个脚本的"自我介绍"（干什么/怎么用/对应计划哪节） |
| `import json` | AI 回复是"JSON 格式的文字"，`json.loads` 转成真字典 |
| `import os` | 读环境变量（API Key 藏哪） |
| `import sys` | 读命令行参数、控制退出码 |
| `from openai import OpenAI` | DeepSeek 接口兼容 OpenAI，用 OpenAI 官方库即可 |
| Key 从环境变量读 | **不写死在代码里**——代码分享/上传 git 就泄露门禁卡 |
| `BASE_URL`/`MODEL` 单独定义 | "换模型只改一行"的来源 |
| `OUTPUT_DIR`（后加） | 输出路径以 `__file__` 为基准——相对路径不相对脚本文件，相对**运行目录**（实踩过的坑） |

### 第 2 块：SYSTEM_PROMPT 说明书（29~104 行）

四要素真身：角色（激活协议领域知识）→ 指令（动词开头）→ 输出格式（JSON 骨架）→ Few-shot 示例（模仿比规则有效）。

- 三引号 `"""\`：跨行大字符串
- JSON 骨架里写"（简短中文）"式说明：**模板 = 骨架 + 填空提示**
- 注意事项段：死规则写进说明书减少低级错
- 坑：GPS 示例是教学假例，等真实协议替换（HANDOFF 坑 #2）

### 第 3 块：analyze_requirement 调 API（107~125 行）

- `client = OpenAI(...)`：接线员（拿 Key + 号码簿）
- `messages` 是**消息列表**：`role="system"` 游戏规则（模型更听），`role="user"` 用户的话；需求经 f-string 拼进 user 消息
- `temperature=0.3`：温度=随机性，协议生成要稳
- `max_tokens=4096`：回复上限，防失控烧钱
- `response.choices[0].message.content.strip()`：快递柜类比——柜子阵列/第一个格子/包裹/信
- 只负责"取"，解析交给下一块（单一职责）

### 第 4 块：_parse_response 容错解析（128~149 行）

最容易出 bug 的地方，LangChain 后来用一行 `JsonOutputParser()` 替代了它。四道保险：

1. 脱 markdown 围栏（AI 爱给 JSON 穿 ` ```json ` 马甲）
2. `json.loads` 直接解析
3. 失败则截第一个 `{` 到**最后一个** `}`（用 `rfind` 从右找，防字段值里有 `}` 提前截断）
4. 再失败：**带着原始输出崩溃**（报错要带证据）

### 第 5 块：print_protocol_table 打印（152~182 行）

- 只打印不返回：**数据与展示分离**的最小形态
- `result.get('key', 'N/A')` 不写 `result['key']`：AI 输出可能缺字段，硬取会 KeyError——防御性编程
- `:<20` 左对齐占 20 字符宽：列对齐全靠它
- 空字段提前 return

### 第 6 块：main 入口（185~211 行）

- `len(sys.argv) < 2` 保护：`argv[0]` 是脚本名，`argv[1]` 才是需求；没传就打用法 + `exit(1)`（0=成功，非 0=失败）
- API 前打印进度提示：调用十几秒，没提示用户以为卡死
- `try/except`：和外部世界打交道必包——崩成一行 `❌ 错误` 而不是几十行堆栈
- 存文件四参数：`"w"` 覆盖 / `encoding="utf-8"`（Windows 默认 GBK 会乱码）/ `ensure_ascii=False`（中文不转义）/ `indent=2`（给人看）
- `if __name__ == "__main__"` 入口哨兵：直接运行才执行 main；被 import 时只加载函数——后面脚本互相 import 全靠它把关

## 自测清单

1. `sys.argv[1]` 是什么？
2. `.get('key', 默认值)` 和 `['key']` 的区别？为什么对 AI 输出用前者？
3. 截取 JSON 时为什么最后一个 `}` 要从右边找（`rfind`）？
4. 不包 try/except 会怎样？
5. `if __name__ == "__main__"` 挡住的是什么事？
