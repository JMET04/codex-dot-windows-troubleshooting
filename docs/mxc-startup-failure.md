# MXC 启动失败：0x80070020

记录日期：2026-10-11。本次桌面包版本为 26.1007.2314.0，安装版 CLI 为 0.162.0 alpha。

## 实际故障

Dot 已把只读检查交给本机工作任务，但终端在脚本启动之前退出，错误为：

```text
MXC launcher: failed to create the process security environment:
CreateProcessSecurityEnvironment failed (HRESULT = 0x80070020)
```

工作任务的回合显示 completed、error=null，不能证明命令成功。该次终端退出码为 1，脚本没有启动，目标聊天未收到测试指令。这是执行环境启动故障，不能仅凭它判断用户没有授权。

## 为什么原有设置没解决

用户配置已经是 `windows.sandbox = "unelevated"`。本机安装包的只读代码检查发现，Windows 桌面会向本地执行器传入 `features.prefer_mxc=true`。因此，仅看到旧版沙盒配置并不足以确定最终使用哪种执行环境。

本机对照检查结果：

| 条件 | 结果 |
| --- | --- |
| 明确选择 MXC | 复现同一启动错误 |
| unelevated 且 prefer_mxc=false | 输出预定标记，退出码 0 |
| 新增 managed_config.toml 默认 prefer_mxc=false，但调用传入 true | 仍失败；新建试验文件已回滚 |
| requirements 禁用 MXC，同时调用仍传入 prefer_mxc=true | 输出预定标记，退出码 0 |

## 本次采用的限制

在官方 Windows 系统策略位置 `%ProgramData%\OpenAI\Codex\requirements.toml` 新增以下限制。本机原先没有此文件；未覆盖已有策略。

```toml
[windows]
allow_mxc = false
```

这是系统范围的配置，会影响之后读取该策略的本地执行器。它阻止选用 MXC，不授予完全访问，也不取代其他权限要求。已有任务可能保留加载过的配置，必须由 Dot 自己重新启动命令验证，不能用独立 CLI 的成功替代。

本机已通过以下官方 CLI 检查：

```powershell
codex -c features.prefer_mxc=true sandbox --include-managed-config --permission-profile :workspace -- cmd.exe /d /c echo REQUIRED_LEGACY_OK
```

输出 `REQUIRED_LEGACY_OK`，退出码 0。用户已有的 unelevated 配置继续适用。旧版沙盒隔离能力较弱，此限制应在确认 MXC 故障已修复后撤销。

随后 Dot 通过原有本机工作任务只调用一次终端，实际输出另一枚预定校验标记，退出码 0，无启动错误。该回合已结束。这确认修复在 Dot 的执行链上也生效，而非仅在排查者独立 CLI 生效；此次没有向目标聊天发消息。

下一次限定聊天验收未通过。Dot 的本机任务实际运行了验收脚本，但创建指定通道回执文件时得到 `PermissionError: [Errno 13] Permission denied`，退出码 1。预约与结果文件均不存在，目标发送次数为 0；没有重试。该任务自己的正式桌面聊天读取工具也返回 `MCP error -32000: Codex app tool request failed`，另一项 stdio 只读初始化检查提前结束。这些结果不能被之前的终端启动成功覆盖。排查者具有完全访问，不代表 Dot 的另一项本机任务拥有同样目录权限；尚需核对该任务的实际授权范围。

随后 Dot 的原工作任务报告自己的运行范围是 `workspace-write`、`auto_review`，可写当前工作目录，且没有暴露目录授权申请工具。该任务在自己的工作目录新建隔离的通道目录，独占创建测试 JSON 并完整读回；读回检查退出码 0。排查者也独立读取到了同一实际文件。文件往返可以放在该任务已经获准写入的目录中；没有修改旧通道 ACL，也没有因此扩大全盘权限。新目录可写不等于旧聊天接口或电脑在线通道恢复。

该工作任务随后在此目录独占写出限定请求。桌面执行者检查目标实时空闲、独占预约后，通过正式接口发送一次。目标实际回合随后为 `interrupted`，没有助手回复；失败回执现已保存，未重发，Dot 的读回验收仍未完成。同期应用重启不能单独证明是谁触发中断。

另发现应用保存的完全访问与自动续跑实际只读权限不一致；普通人工消息启动的回合恢复完全访问。已补充并核对官方默认权限配置档，续跑是否稳定仍需实测。此问题、云端 HTTP 403 和启动诊断改进详见[后续记录](permissions-and-diagnostics-2026-10-11.md)，不能用终端启动通过替代这些验收。

## 回滚与验收边界

修改前备份原策略。如果文件原先不存在，且仍完全是自己创建的内容，回滚时可移除该文件；如果文件已有其他条目，只撤销自己新增的一项。不要覆盖企业策略或删除后来新增的内容。

这项本机启动修复与在线通道的 WebSocket HTTP 403 分开处理。独立命令成功不证明 Dot 原生直连恢复，也不证明 Dot 能控制所有桌面软件。后续应核对 Dot 自己的终端退出码、真实任务回合、目标实际回复；超时或 UNKNOWN 请求不得直接重发。

依据：[官方 Windows 沙盒说明](https://learn.chatgpt.com/docs/windows/windows-sandbox)、[官方托管配置位置与优先级](https://learn.chatgpt.com/docs/enterprise/managed-configuration)。[OpenAI 仓库的同类公开报告](https://github.com/openai/codex/issues/52752)仅说明有人报告相同错误，不构成官方已确认根因或已发布修复的证据。
