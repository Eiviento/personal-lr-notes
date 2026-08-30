> 临时素材笔记（Task 1 产物），供 LangChain API 参考手册各段直接抄用。手册完成后删除本文件。

## 版本基线

> 获取方式：项目根目录下，用 `E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe`（agent_env）执行。Python 版本输出前总带一行无害警告：`RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!`，下略。

| 包 | 版本 | 获取命令 |
|---|---|---|
| langchain_core | 1.4.9 | `langchain_core.__version__` |
| langchain_openai | 1.3.5 | `langchain_openai.__version__` |
| chromadb | 1.5.9 | `chromadb.__version__` |
| langgraph | 1.2.9 | `importlib.metadata.version("langgraph")` |
| onnxruntime | 1.23.2 | `importlib.metadata.version("onnxruntime")` |

**版本差异证据（照录原命令报错）：**

命令 1 原样运行（`import langchain_core, langchain_openai, chromadb, langgraph, onnxruntime; print(...__version__)`）报错，前三个包先打出、langgraph 处中断：

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
AttributeError: module 'langgraph' has no attribute '__version__'
langchain_core 1.4.9
langchain_openai 1.3.5
chromadb 1.5.9
```

→ langgraph 1.2.9 不再暴露 `__version__` 属性，改用 `importlib.metadata.version("langgraph")` 取到 1.2.9；onnxruntime 同样用 `importlib.metadata.version("onnxruntime")` 取到 1.23.2。

## 词条签名

> 每条为 `inspect.signature` 原文输出 + 关键参数一句话。**行内 `版本差异证据` 为报错原文照录。**

### ChatPromptTemplate
```text
(self, messages: 'Sequence[MessageLikeRepresentation]', *, template_format: 'PromptTemplateFormat' = 'f-string', **kwargs: 'Any') -> 'None'
(messages: 'Sequence[MessageLikeRepresentation]', template_format: 'PromptTemplateFormat' = 'f-string') -> 'ChatPromptTemplate'
```
关键参数：`messages` 是消息元组序列（如 `("system", "...")` / `("human", "...")`）；构造用 `ChatPromptTemplate.from_messages([...])`，`template_format` 默认 `f-string`。

### ChatOpenAI
```text
(self, *args: Any, **kwargs: Any) -> None
```
关键参数：`__init__` 参数全部经 `**kwargs` 由 pydantic 配置（`model`、`temperature`、`api_key`、`base_url` 等），直接 `ChatOpenAI(model=..., temperature=...)` 调用。

### with_retry
```text
(self, *, retry_if_exception_type: 'tuple[type[BaseException], ...]' = (<class 'Exception'>,), wait_exponential_jitter: 'bool' = True, exponential_jitter_params: 'ExponentialJitterParams | None' = None, stop_after_attempt: 'int' = 3) -> 'Runnable[Input, Output]'
```
关键参数：`stop_after_attempt`（最大尝试次数，默认 3）、`wait_exponential_jitter`（指数退避+抖动，默认 True）、`retry_if_exception_type`（重试哪些异常，默认 `Exception`）。定义在 `Runnable` 基类上（命令 3 输出此签名后即报 bind_tools 错误，见下）。

### bind_tools
```text
(self, tools: 'Sequence[dict[str, Any] | type | Callable | BaseTool]', *, tool_choice: 'dict | str | bool | None' = None, strict: 'bool | None' = None, parallel_tool_calls: 'bool | None' = None, response_format: '_DictOrPydanticClass | None' = None, **kwargs: 'Any') -> 'Runnable[LanguageModelInput, AIMessage]'
```
关键参数：`tools`（函数/模型/BaseTool 列表，把签名发给模型）、`tool_choice`（强制选择工具）、`strict`（严格模式）、`parallel_tool_calls`（并行工具调用）。

**版本差异证据（照录）：** 命令 3 原样运行在 `bind_tools` 处报错：

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
AttributeError: type object 'Runnable' has no attribute 'bind_tools'
invoke: (self, input: 'Input', config: 'RunnableConfig | None' = None, **kwargs: 'Any') -> 'Output'
batch: (self, inputs: 'list[Input]', config: 'RunnableConfig | list[RunnableConfig] | None' = None, *, return_exceptions: 'bool' = False, **kwargs: 'Any | None') -> 'list[Output]'
stream: (self, input: 'Input', config: 'RunnableConfig | None' = None, **kwargs: 'Any | None') -> 'Iterator[Output]'
with_retry: (self, *, retry_if_exception_type: 'tuple[type[BaseException], ...]' = (<class 'Exception'>,), wait_exponential_jitter: 'bool' = True, exponential_jitter_params: 'ExponentialJitterParams | None' = None, stop_after_attempt: 'int' = 3) -> 'Runnable[Input, Output]'
```

→ langchain_core 1.4.9 中 `bind_tools` 不在 `Runnable` 基类上；经 `ChatOpenAI.bind_tools` 取到签名（定义类 `langchain_openai.chat_models.base.BaseChatOpenAI`）。`RunnablePassthrough` 未被原命令 import，`assign` 另行补取。

### 管道运算符|
```text
(self, other: 'Runnable[Output, Other] | Callable[[Iterator[Output]], Iterator[Other]] | Callable[[AsyncIterator[Output]], AsyncIterator[Other]] | Callable[[Output], Other] | Mapping[str, Runnable[Output, Any] | Callable[[Output], Any] | Any]') -> 'RunnableSerializable[Input, Any]'
```
关键参数：`self` 是左侧 Runnable，`other` 是右侧 Runnable/函数/Mapping；`a | b | c` 顺序串联成一条 LCEL 管道（`Runnable.__or__`，命令来自补取）。

### RunnableLambda
```text
(self, func: 'Callable[[Input], Iterator[Output]] | Callable[[Input], Runnable[Input, Output]] | Callable[[Input], Output] | Callable[[Input, RunnableConfig], Output] | Callable[[Input, CallbackManagerForChainRun], Output] | Callable[[Input, CallbackManagerForChainRun, RunnableConfig], Output] | Callable[[Input], Awaitable[Output]] | Callable[[Input], AsyncIterator[Output]] | Callable[[Input, RunnableConfig], Awaitable[Output]] | Callable[[Input, AsyncCallbackManagerForChainRun], Awaitable[Output]] | Callable[[Input, AsyncCallbackManagerForChainRun, RunnableConfig], Awaitable[Output]]', afunc: 'Callable[[Input], Awaitable[Output]] | Callable[[Input], AsyncIterator[Output]] | Callable[[Input, RunnableConfig], Awaitable[Output]] | Callable[[Input, AsyncCallbackManagerForChainRun], Awaitable[Output]] | Callable[[Input, AsyncCallbackManagerForChainRun, RunnableConfig], Awaitable[Output]] | None' = None, name: 'str | None' = None) -> 'None'
```
关键参数：`func`（同步 Python 函数，可接收 `Input` 或 `Input, RunnableConfig`）、`afunc`（可选异步版）、`name`（可选命名）。普通函数经它包装成管道可用 Runnable。

### RunnablePassthrough
```text
(self, func: 'Callable[[Other], None] | Callable[[Other, RunnableConfig], None] | Callable[[Other], Awaitable[None]] | Callable[[Other, RunnableConfig], Awaitable[None]] | None' = None, afunc: 'Callable[[Other], Awaitable[None]] | Callable[[Other, RunnableConfig], Awaitable[None]] | None' = None, *, input_type: 'type[Other] | None' = None, **kwargs: 'Any') -> 'None'
```
关键参数：无参 `RunnablePassthrough()` 原样透传 dict；`assign()` 返回新的 `RunnableAssign` 追加字段；`func`/`afunc` 是旁路副作用钩子。

### RunnableParallel
```text
(self, steps__: 'Mapping[str, Runnable[Input, Any] | Callable[[Input], Any] | Mapping[str, Runnable[Input, Any] | Callable[[Input], Any]]] | None' = None, **kwargs: 'Runnable[Input, Any] | Callable[[Input], Any] | Mapping[str, Runnable[Input, Any] | Callable[[Input], Any]]') -> 'None'
```
关键参数：每个关键字参数即一个分支（`a=chain1, b=chain2`），并行执行后合并成 dict；`steps__` 位置参数等价形式。

### assign
```text
(**kwargs: 'Runnable[dict[str, Any], Any] | Callable[[dict[str, Any]], Any] | Mapping[str, Runnable[dict[str, Any], Any] | Callable[[dict[str, Any]], Any]]') -> 'RunnableAssign'
```
关键参数：每个关键字=一个子链/函数，往输入 dict 追加对应键，返回 `RunnableAssign`；常连用 `| RunnablePassthrough.assign(键=子链)`。

### invoke/batch/stream
```text
invoke: (self, input: 'Input', config: 'RunnableConfig | None' = None, **kwargs: 'Any') -> 'Output'
batch: (self, inputs: 'list[Input]', config: 'RunnableConfig | list[RunnableConfig] | None' = None, *, return_exceptions: 'bool' = False, **kwargs: 'Any | None') -> 'list[Output]'
stream: (self, input: 'Input', config: 'RunnableConfig | None' = None, **kwargs: 'Any | None') -> 'Iterator[Output]'
```
关键参数：`invoke` 单输入返回完整输出；`batch` 输入列表、`return_exceptions` 为 True 时单条失败不中断；`stream` 按块产出迭代器。

### StrOutputParser
```text
(self, *args: Any, **kwargs: Any) -> None
```
关键参数：无参构造 `StrOutputParser()`；把 LLM 的 AIMessage 输出转成纯字符串。

### JsonOutputParser
```text
(self, *args: Any, **kwargs: Any) -> None
```
关键参数：无参构造 `JsonOutputParser()`；把 LLM 输出解析成 dict，内置容错（部分解析）。

### SystemMessage/HumanMessage/ToolMessage
```text
SystemMessage: (self, content: str | list[str | dict[typing.Any, typing.Any]] | None = None, content_blocks: list[langchain_core.messages.content.TextContentBlock | langchain_core.messages.content.InvalidToolCall | langchain_core.messages.content.ReasoningContentBlock | langchain_core.messages.content.NonStandardContentBlock | langchain_core.messages.content.ImageContentBlock | langchain_core.messages.content.VideoContentBlock | langchain_core.messages.content.AudioContentBlock | langchain_core.messages.content.PlainTextContentBlock | langchain_core.messages.content.FileContentBlock | langchain_core.messages.content.ToolCall | langchain_core.messages.content.ToolCallChunk | langchain_core.messages.content.ServerToolCall | langchain_core.messages.content.ServerToolCallChunk | langchain_core.messages.content.ServerToolResult] | None = None, **kwargs: Any) -> None
HumanMessage: (self, content: str | list[str | dict[typing.Any, typing.Any]] | None = None, content_blocks: list[langchain_core.messages.content.TextContentBlock | langchain_core.messages.content.InvalidToolCall | langchain_core.messages.content.ReasoningContentBlock | langchain_core.messages.content.NonStandardContentBlock | langchain_core.messages.content.ImageContentBlock | langchain_core.messages.content.VideoContentBlock | langchain_core.messages.content.AudioContentBlock | langchain_core.messages.content.PlainTextContentBlock | langchain_core.messages.content.FileContentBlock | langchain_core.messages.content.ToolCall | langchain_core.messages.content.ToolCallChunk | langchain_core.messages.content.ServerToolCall | langchain_core.messages.content.ServerToolCallChunk | langchain_core.messages.content.ServerToolResult] | None = None, **kwargs: Any) -> None
ToolMessage: (self, content: str | list[str | dict[typing.Any, typing.Any]] | None = None, content_blocks: list[langchain_core.messages.content.TextContentBlock | langchain_core.messages.content.InvalidToolCall | langchain_core.messages.content.ReasoningContentBlock | langchain_core.messages.content.NonStandardContentBlock | langchain_core.messages.content.ImageContentBlock | langchain_core.messages.content.VideoContentBlock | langchain_core.messages.content.AudioContentBlock | langchain_core.messages.content.PlainTextContentBlock | langchain_core.messages.content.FileContentBlock | langchain_core.messages.content.ToolCall | langchain_core.messages.content.ToolCallChunk | langchain_core.messages.content.ServerToolCall | langchain_core.messages.content.ServerToolCallChunk | langchain_core.messages.content.ServerToolResult] | None = None, **kwargs: Any) -> None
```
关键参数：`content`（文本内容）、`content_blocks`（结构化内容块）；ToolMessage 还常用 `tool_call_id=`（经 `**kwargs`）关联到模型发出的工具调用。同命令还打出 `AIMessage`，签名与前三个同构，从略。

### @tool
```text
(name_or_callable: str | collections.abc.Callable[..., typing.Any] | None = None, runnable: Optional[langchain_core.runnables.base.Runnable[Any, Any]] = None, *args: Any, description: str | None = None, return_direct: bool = False, args_schema: type[pydantic.main.BaseModel] | type[pydantic.v1.main.BaseModel] | dict[str, typing.Any] | None = None, infer_schema: bool = True, response_format: Literal['content', 'content_and_artifact'] = 'content', parse_docstring: bool = False, error_on_invalid_docstring: bool = True, extras: dict[str, typing.Any] | None = None) -> langchain_core.tools.base.BaseTool | collections.abc.Callable[[typing.Union[collections.abc.Callable[..., typing.Any], langchain_core.runnables.base.Runnable[typing.Any, typing.Any]]], langchain_core.tools.base.BaseTool]
```
关键参数：直接 `@tool`（无括号）或 `@tool(description=..., args_schema=...)`；`infer_schema` 默认从类型注解推断参数 schema；`parse_docstring` 从 docstring 解析描述；`response_format` 可选 `'content'` 或 `'content_and_artifact'`。

### StateGraph/START/END
```text
StateGraph: (self, state_schema: 'type[StateT]', context_schema: 'type[ContextT] | None' = None, *, input_schema: 'type[InputT] | None' = None, output_schema: 'type[OutputT] | None' = None, **kwargs: 'Unpack[DeprecatedKwargs]') -> 'None'
add_node: (self, node: 'str | StateNode[NodeInputT, ContextT]', action: 'StateNode[NodeInputT, ContextT] | None' = None, *, defer: 'bool' = False, metadata: 'dict[str, Any] | None' = None, input_schema: 'type[NodeInputT] | None' = None, retry_policy: 'RetryPolicy | Sequence[RetryPolicy] | None' = None, cache_policy: 'CachePolicy | None' = None, error_handler: 'StateNode[Any, ContextT] | None' = None, destinations: 'dict[str, str] | tuple[str, ...] | None' = None, timeout: 'float | timedelta | TimeoutPolicy | None' = None, **kwargs: 'Unpack[DeprecatedKwargs]') -> 'Self'
add_edge: (self, start_key: 'str | list[str]', end_key: 'str') -> 'Self'
add_conditional_edges: (self, source: 'str', path: 'Callable[..., Hashable | Sequence[Hashable]] | Callable[..., Awaitable[Hashable | Sequence[Hashable]]] | Runnable[Any, Hashable | Sequence[Hashable]]', path_map: 'dict[Hashable, str] | list[str] | None' = None) -> 'Self'
```
关键参数：`state_schema`（状态 schema，必填）；`add_node(node, action)`（`action` 可为字符串函数名或函数）；`add_edge(start_key, end_key)`；`add_conditional_edges(source, path, path_map)`（`path` 返回分支键，`path_map` 映射到节点名）。`START`/`END` 是图内置哨兵常量，`g.add_edge(START, "analyze")`、`g.add_edge("merge", END)`。

### chromadb EmbeddingFunction/Embeddings/Documents
```text
PersistentClient.__init__: (*args, **kwargs)
Client.get_or_create_collection: (self, name: str, schema: Optional[chromadb.api.types.Schema] = None, configuration: Optional[chromadb.api.collection_configuration.CreateCollectionConfiguration] = None, metadata: Optional[Dict[str, Any]] = None, embedding_function: Optional[chromadb.api.types.EmbeddingFunction[Union[List[str], List[numpy.ndarray[tuple[int, ...], numpy.dtype[Union[numpy.uint64, numpy.int64, numpy.float64]]]]]]] = <chromadb.api.types.DefaultEmbeddingFunction object at 0x000001F77F9E8D30>, data_loader: Optional[chromadb.api.types.DataLoader[List[Optional[numpy.ndarray[tuple[int, ...], numpy.dtype[Union[numpy.uint64, numpy.int64, numpy.float64]]]]]]] = None) -> chromadb.api.models.Collection.Collection
Collection.query: (self, query_embeddings: Union[numpy.ndarray[tuple[int, ...], numpy.dtype[Union[numpy.int32, numpy.float32]]], List[numpy.ndarray[tuple[int, ...], numpy.dtype[Union[numpy.int32, numpy.float32]]]], Sequence[float], Sequence[int], List[Union[Sequence[float], Sequence[int]]], NoneType] = None, query_texts: Union[str, List[str], NoneType] = None, query_images: Union[numpy.ndarray[tuple[int, ...], numpy.dtype[Union[numpy.uint64, numpy.int64, numpy.float64]]], List[numpy.ndarray[tuple[int, ...], numpy.dtype[Union[numpy.uint64, numpy.int64, numpy.float64]]]], NoneType] = None, query_uris: Union[str, List[str], NoneType] = None, ids: Union[str, List[str], NoneType] = None, n_results: int = 10, where: Optional[Dict[Union[str, Literal['$and'], Literal['$or']], Union[str, int, float, bool, Dict[Union[Literal['$gt'], Literal['$gte'], Literal['$lt'], Literal['$lte'], Literal['$ne'], Literal['$eq'], Literal['$and'], Literal['$or']], Union[str, int, float, bool]], Dict[Union[Literal['$in'], Literal['$nin']], List[Union[str, int, float, bool]]], Dict[Union[Literal['$contains'], Literal['$not_contains']], Union[str, int, float, bool]], List[ForwardRef('Where')]]]] = None, where_document: Optional[Dict[Union[Literal['$contains'], Literal['$not_contains'], Literal['$regex'], Literal['$not_regex'], Literal['$and'], Literal['$or']], Union[str, List[ForwardRef('WhereDocument')]]]] = None, include: List[Literal['documents', 'embeddings', 'metadatas', 'distances', 'uris', 'data']] = ['metadatas', 'documents', 'distances']) -> chromadb.api.types.QueryResult
Collection.upsert: (self, ids: Union[str, List[str]], embeddings: Union[numpy.ndarray[tuple[int, ...], numpy.dtype[Union[numpy.int32, numpy.float32]]], List[numpy.ndarray[tuple[int, ...], numpy.dtype[Union[numpy.int32, numpy.float32]]]], Sequence[float], Sequence[int], List[Union[Sequence[float], Sequence[int]]], NoneType] = None, metadatas: Union[Mapping[str, Union[str, int, float, bool, chromadb.base_types.SparseVector, List[Union[str, int, float, bool]], NoneType]], List[Mapping[str, Union[str, int, float, bool, chromadb.base_types.SparseVector, List[Union[str, int, float, bool]], NoneType]]], NoneType] = None, documents: Union[str, List[str], NoneType] = None, images: Union[numpy.ndarray[tuple[int, ...], numpy.dtype[Union[numpy.uint64, numpy.int64, numpy.float64]]], List[numpy.ndarray[tuple[int, ...], numpy.dtype[Union[numpy.uint64, numpy.int64, numpy.float64]]]], NoneType] = None, uris: Union[str, List[str], NoneType] = None) -> None
EmbeddingFunction.__call__: (self, input: -D) -> List[numpy.ndarray[tuple[int, ...], numpy.dtype[Union[numpy.int32, numpy.float32]]]]
EmbeddingFunction: <class 'chromadb.api.types.EmbeddingFunction'>
Embeddings: typing.List[numpy.ndarray[tuple[int, ...], numpy.dtype[typing.Union[numpy.int32, numpy.float32]]]]
Documents: typing.List[str]
```
关键参数：`EmbeddingFunction` 是协议类，实现 `__call__(input: Documents) -> Embeddings`（`-D` 是 chromadb 1.5.9 对 `Documents` 别名（`List[str]`）的渲染显示，照录原文）；`Embeddings = List[numpy.ndarray]`、`Documents = List[str]`；`PersistentClient(path=...)`；`get_or_create_collection(name, embedding_function=...)` 返回 `Collection`；`Collection.query(query_texts=[...], n_results=k)`；`Collection.upsert(ids=..., documents=..., embeddings=...)`。

**版本差异证据（照录）：** 命令 8 原样运行报错——chromadb 1.5.9 中 `chromadb.Client` 是工厂函数，不能 `chromadb.Client.get_or_create_collection`；`query`/`upsert` 在 `Collection` 上而非 Client 上：

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
AttributeError: 'function' object has no attribute 'get_or_create_collection'
PersistentClient: (*args, **kwargs)
```

另：实例化 `PersistentClient(path=':memory:')` 在本机 Windows 报 `chromadb.errors.InternalError: 文件名、目录名或卷标语法不正确。 (os error 123)`（rust 绑定启动失败，环境差异），故签名改为直接对类方法 `inspect.signature`（不连库）。

## 行号引用

> 每词条一行：词条名 + `scripts/xxx.py:行号` 多处引用。行号来自 `grep -n` 原文。

- **ChatPromptTemplate**: scripts/demo_parallel_merge.py:25,32,39,46; scripts/phase2_1_langchain_basics.py:8,17,30,38; scripts/phase2_2_lcel_pipeline.py:36,49; scripts/phase2_3_output_parsers.py:23,36,49; scripts/phase3_1_doc_input.py:21,47; scripts/phase3_2_prompt_chain.py:32,46,59,81; scripts/phase4_1_rag.py:40
- **ChatOpenAI**: scripts/phase2_1_langchain_basics.py:89; scripts/phase2_2_lcel_pipeline.py:72; scripts/phase2_3_output_parsers.py:73; scripts/phase3_1_doc_input.py:137; scripts/phase3_2_prompt_chain.py:98; scripts/phase5_2_robust.py:91
- **with_retry**: scripts/phase5_2_robust.py:11,55,96
- **bind_tools**: scripts/phase4_2_tool_calling.py:60,61
- **管道运算符|**: scripts/demo_parallel_merge.py:69,70,72; scripts/generate_protocol.py:35,36,37; scripts/phase2_1_langchain_basics.py:114; scripts/phase2_2_lcel_pipeline.py:81; scripts/phase2_3_output_parsers.py:93,102; scripts/phase3_1_doc_input.py:144; scripts/phase3_2_prompt_chain.py:107,108,109,140,141,142,143; scripts/phase3_3_batch_stream.py:37,38,39; scripts/phase4_1_rag.py:205,210,211,212,213; scripts/phase4_3_human_review.py:55; scripts/phase5_2_robust.py:57,58,59,60
- **RunnableLambda**: scripts/demo_invoke_batch_stream.py:15,24,46; scripts/demo_parallel_merge.py:26,63; scripts/demo_stream_feel.py:13,23; scripts/generate_protocol.py:27,37; scripts/phase2_2_lcel_pipeline.py:5,37,84,85,123,125,126,127; scripts/phase3_2_prompt_chain.py:33,122,143; scripts/phase3_3_batch_stream.py:27,39; scripts/phase4_1_rag.py:41,213; scripts/phase5_2_robust.py:31,60
- **RunnablePassthrough**: scripts/generate_protocol.py:27,34,35,36; scripts/phase2_2_lcel_pipeline.py:8,37,121,129; scripts/phase3_2_prompt_chain.py:21,33,140,141,142; scripts/phase3_3_batch_stream.py:27,36,37,38; scripts/phase4_1_rag.py:41,209,210,211,212; scripts/phase5_2_robust.py:31,57,58,59
- **RunnableParallel**: scripts/demo_parallel_merge.py:26,68; scripts/phase2_2_lcel_pipeline.py:6,22,37,118,123
- **assign**: scripts/generate_protocol.py:34,35,36; scripts/phase2_2_lcel_pipeline.py:7; scripts/phase3_2_prompt_chain.py:21,140,141,142; scripts/phase3_3_batch_stream.py:36,37,38; scripts/phase4_1_rag.py:209,210,211,212; scripts/phase5_2_robust.py:57,58,59
- **invoke/batch/stream**: invoke — scripts/demo_2_2_checks.py:39,58; scripts/demo_invoke_batch_stream.py:28; scripts/demo_parallel_merge.py:79; scripts/demo_stream_feel.py:27; scripts/extra_langgraph_intro.py:46,50,54,88,130,145; scripts/generate_protocol.py:100; scripts/phase2_1_langchain_basics.py:87,159; scripts/phase2_2_lcel_pipeline.py:190; scripts/phase2_3_output_parsers.py:85,94,103; scripts/phase3_1_doc_input.py:147; scripts/phase3_2_prompt_chain.py:196; scripts/phase4_1_rag.py:221,226; scripts/phase4_2_tool_calling.py:66,78; scripts/phase4_3_human_review.py:127; batch — scripts/demo_invoke_batch_stream.py:33; scripts/generate_protocol.py:100; scripts/phase3_3_batch_stream.py:58; stream — scripts/demo_invoke_batch_stream.py:46; scripts/demo_stream_feel.py:33; scripts/phase3_3_batch_stream.py:75
- **StrOutputParser**: scripts/demo_parallel_merge.py:24,69,70; scripts/phase2_3_output_parsers.py:2,7,8,14,15,22,92,93,96; scripts/phase3_2_prompt_chain.py:12,31,107; scripts/phase5_2_robust.py:30,57
- **JsonOutputParser**: scripts/demo_parallel_merge.py:24,72; scripts/phase2_1_langchain_basics.py:8,18,98,103,105; scripts/phase2_2_lcel_pipeline.py:35,80; scripts/phase2_3_output_parsers.py:2,8,15,22,101,102,105; scripts/phase3_1_doc_input.py:20,144; scripts/phase3_2_prompt_chain.py:14,16,31,108,109; scripts/phase4_1_rag.py:39,205; scripts/phase4_3_human_review.py:32,55; scripts/phase5_2_robust.py:30,58,59
- **SystemMessage/HumanMessage/ToolMessage**: scripts/extra_langgraph_intro.py:22,93,98,140,143; scripts/phase4_2_tool_calling.py:10,26,76,100,105
- **@tool**: scripts/phase4_2_tool_calling.py:41
- **StateGraph/START/END**: scripts/extra_langgraph_intro.py:23,64,70,71,72,73,74,106,110,113,114,115,147
- **chromadb EmbeddingFunction/Embeddings/Documents**: scripts/phase4_1_rag.py:18,38,104,105,116,142,144,163,175
