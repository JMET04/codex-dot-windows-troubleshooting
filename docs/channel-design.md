# 文件与本机任务通道

使用已有能力优先：Dot 的已连接电脑任务、本机正式聊天工具、普通工作目录。文件通道只是传递请求与结果，不能创造不存在的工具权限。

## 文件协议

在用户批准的工作目录内准备 inbox、outbox、evidence。每次请求带唯一 request_id、随机 nonce、授权目标、允许的操作范围和期待结果；回件明确区分 executor_started、file_round_trip、message_accepted、turn_completed 与 actual_reply。

示例见 [request.example.json](../examples/request.example.json)。这里没有后台监听服务；向 Dot 正常发送文件路径，或者通过用户已授权的界面输入通知。当前聊天之间的消息须有用户授权。

## 已有聊天指令的检查顺序

1. 取得准确目标和授权范围；不要把 room_id、标题或其它标识猜成 threadId。
2. 通过实际桌面接口检查目标和最新回合状态，记录时间。
3. 缺少本机正式工具时，可启动自己的官方 app-server stdio 客户端。使用安装版 schema，不自行猜测字段。
4. 发送前再次核对最新回合未变化。
5. 独占创建预约文件，固定目标、nonce、请求编号；重复调用遇到预约应停止核查，不删文件重试。
6. 发送后保留接受的 turnId，等待完成；若超时，不立即重发。
7. 独立读取目标真实消息与回复，比较精确回合、状态和校验码。

独占预约减少重复发送，**不是跨服务端的 exactly-once 保证**。发送成功但写预约更新失败时，仍要查实际目标。进程之间的服务加载状态也不能替代桌面空闲状态；检查与发送之间仍存在竞争窗口，应保持目标无人继续操作。

## stdio 路径

先 initialize，再 initialized；只读查询用 thread/read（includeTurns=false）。受明确授权的控制验证曾用 thread/turns/list、thread/resume、turn/start，并读取完成事件。它复用正常账户与任务权限，不覆盖 sandbox、approval_policy 或模型设置，不开放网络控制端口。

本仓库的 [probe_local_task.py](../scripts/probe_local_task.py) **只读元数据**，不包含发送、恢复或通用控制。其独立进程的 notLoaded 不表示桌面空闲。

仅看到 completed 不够：还须核对结果。仅看到 message_accepted 也不表示最终完成。可用 [verify_receipts.py](../scripts/verify_receipts.py) 离线核对指定格式的两份报告；它不能证明提供的报告来自真正接口，需要调用者先核对来源。
