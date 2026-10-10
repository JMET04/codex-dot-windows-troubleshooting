# 官方来源与推断边界

查询日期：2026-10-10。官方内容会更新，本案例是当日环境的记录。

| 来源 | 支持的内容 |
| --- | --- |
| [Windows 沙盒指南](https://learn.chatgpt.com/docs/windows/windows-sandbox) | 实现选择、备用模式及隔离限制、受管配置和故障分支 |
| [配置基础](https://learn.chatgpt.com/docs/config-file/config-basic) | [windows] sandbox 配置入口 |
| [PR #51822](https://github.com/openai/codex/pull/51822) | 对活跃 EXE/DLL 打开过宽访问可能导致共享冲突；对应修复已合并 |
| [Dot 任务与记忆](https://learn.chatgpt.com/docs/dots/tasks-and-memory) | 已连接电脑上的新任务与现有本机 Codex 任务能力；连接不自动开放所有历史聊天 |
| [Dot 电脑与应用连接](https://learn.chatgpt.com/docs/dots/computers-and-apps) | Dot 本机权限单独授权，电脑在线且应用打开 |
| [Codex App Server](https://learn.chatgpt.com/docs/app-server) | stdio 初始化、线程与回合接口、由安装版本生成 schema |
| [Microsoft 分页文件容量](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/how-to-determine-the-appropriate-page-file-size-for-64-bit-versions-of-windows) | 提交上限、峰值负载和磁盘条件决定所需容量 |
| [Microsoft 内存分配与分页文件增长](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/slow-page-file-growth-memory-allocation-errors) | 内存分配失败的容量/增长因素及重启生效要求 |
| [Computer Use](https://learn.chatgpt.com/docs/computer-use) | Work/Codex 的 Windows 电脑控制及插件、执行环境与应用许可要求 |

本案例 Windows 日志与官方 PR 的机制相符，这是对证据的推断；没有逆向证明每个内部调用，也没有证明当前所有发行版本都包含该修复。

cloud placement 格式错误和 durable 403 的关联未确认。不能仅凭错误确定灰度范围、账号资格或服务端具体缺陷。

当前官方文档倾向于兼容设备使用 MXC；本案例实际验证的是旧实现的 unelevated 回退。不能用本案例宣称 MXC 已验证。

仓库未复制官方全文，官方页面是规范信息的首选来源。
