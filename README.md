# Codex / Dot 在 Windows 上提示“没权限”：排查与修复案例

一份来自实际排查的中文参考资料，记录于 **2026-10-10**。适用于 Dot 的电脑显示“已连接”，但本机任务无法启动、文件通道不可用，或对已有聊天的访问报错时。

本案例恢复了 **本机执行、文件往返、任务信息读取，以及向一个已授权现有聊天发送指令并收到真实回复**。云端原生访问旧本机聊天仍存在错误；并未验证所有软件的鼠标键盘控制。

## 快速判断

| 现象 | 先检查什么 | 本案例结果 |
| --- | --- | --- |
| 电脑离线或未授权 | Dot 自己的电脑连接权限 | 本案例已连接且已授权 |
| 命令尚未创建就失败 | Windows 沙盒初始化日志 | elevated 初始化触发文件占用错误 32 |
| 命令能启动，写指定文件被拒绝 | 该任务的目录权限、正式授权机制 | 与初始化故障分开处理 |
| cloud_threads_read 报 placement 格式错误 | 云端接口与目标本机聊天兼容性 | 本机官方接口可读取，云端路径仍失败 |
| 启动调用超时 | 目标实际回合、回执文件 | 请求后来执行成功，不能直接重发 |

## 阅读顺序

1. [修复与回滚步骤](docs/repair-guide.md)：按错误类型选择方案。
2. [案例记录](docs/case-study.md)：原因、未成功的尝试、实际验证和剩余限制。
3. [文件与任务通道](docs/channel-design.md)：如何避免重复发送和虚假成功。
4. [官方依据](docs/sources.md)：链接、查询日期及推断边界。
5. [公开数据说明](docs/public-data.md)：哪些是脱敏实测，哪些是演示样例。

## 本案例最关键的配置变更

仅在日志指向 elevated 初始化失败、且环境政策允许时，备份配置，再修改**现有**的 Windows 段：

```toml
[windows]
sandbox = "unelevated"
```

这属于旧版沙盒的备用方案。官方当前优先建议兼容设备使用 MXC；unelevated 的网络隔离较弱，不支持 denied read paths。它不是长期普遍推荐，也不修复云端路由错误。完整适用条件和回滚方法见[指南](docs/repair-guide.md)。

## 辅助工具

- `scripts/probe_local_task.py`：通过安装版官方 app-server 读取一个指定聊天的元数据；不读聊天内容、不恢复任务、不发送指令。报告可能含本机路径和聊天名称，保持本地。
- `scripts/verify_receipts.py`：离线比较“发送方结果”和“目标实际回执”，要求回合完成、目标和回合一致、回复完全匹配。
- `examples/`：合成的协议与回执样例；**不是新的实测结果**。
- `evidence/case-summary.redacted.json`：从原始本机证据核对后生成的脱敏事实摘要；原始记录不在仓库内。
- `MANIFEST.sha256`：发布源文件清单及校验值。

```powershell
python scripts/probe_local_task.py --help
python scripts/verify_receipts.py examples/sender-result.json examples/target-receipt.json
python -m unittest discover -s tests -v
```

下载完整 ZIP 请打开 [Releases](https://github.com/JMET04/codex-dot-windows-troubleshooting/releases)。

资料反映一个环境的一次排查。按自己的错误与版本核对，不把“已连接”“工具存在”“回合完成”单独当作工作成功的证据。
