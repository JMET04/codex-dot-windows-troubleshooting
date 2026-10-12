# Codex / Dot 在 Windows 上提示“没权限”：排查与修复案例

一份来自实际排查的中文参考资料，更新于 **2026-10-12**。适用于 Dot 的电脑显示“已连接”，但本机任务无法启动、文件通道不可用，或对已有聊天的访问报错时。

**私人 Pages 双向通讯验收：** 新请求由 Dot 生成，原本地项目实际收到后亲自读取同页并写回回执，Dot 再读回并写确认；页面预览及后续正式 API 读取均确认三段持久化 JSON 一致。此次转交由检修聊天完成，自动收件尚未部署，期间本地 API 也发生过网络错误；原生电脑连接仍未恢复。[往返证据与使用范围](docs/pages-bidirectional-channel.md)。

此前一轮曾恢复 **本机执行、文件往返、任务信息读取，以及向一个已授权现有聊天发送指令并收到真实回复**。后续复测仍存在失败：最新限定委托已中断且没有回复，云端连接仍报错，不能将历史通过视为当前稳定恢复；并未验证所有软件的鼠标键盘控制。

**同日复发更新：** 后续另一个项目对接遇到服务断开，查到 app-server 内存分配失败和 Windows 虚拟内存不足记录。新增分页文件已由系统实际分配，提交上限约从 32.7 GiB 增至 45.1 GiB；另修正失败代理路径和过大的状态读取。[复发证据与恢复边界](docs/recurrence-2026-10-10.md)。首次通过不代表后续持续稳定。

**电脑离线更新：** 后续在线通道反复遭遇 WebSocket HTTP 403，本机任务接口和普通模型连接仍可用。官方已有会话刷新已执行，桌面在线通道仍未恢复；这项故障与沙盒、内存及任务工具缺失分别检查。[在线通道排查记录](docs/offline-online-channel.md)。

**桌面更新兼容修复：** 桌面更新移除了旧 CLI 缓存目录，导致原来写死程序路径的文件通道工具无法启动。工具现已自动发现安装版 CLI，本机只读查询和 7 项测试通过。月儿派发诊断任务仍返回 `UNKNOWN`，直接电脑控制尚未恢复。[更新兼容性与本次验证](docs/runtime-update-compatibility.md)。

**有限委托测试：** 月儿在主聊天输出限定请求，桌面执行者将请求转录到文件并实际新建记事本文档、输入测试文字、回传结果。首次标点转录错误被月儿核对发现，已在同一文档修正。此方式需要桌面执行者在场，原生直连仍未恢复。[屏幕与文件委托记录](docs/screen-file-delegation.md)。

**MXC 再次启动失败：** Dot 本机工作任务实际遇到 `CreateProcessSecurityEnvironment failed (HRESULT = 0x80070020)`。系统 requirements 限制 `windows.allow_mxc=false` 后，独立 CLI 和 Dot 自己的终端检查均通过，退出码 0。随后聊天验收因通道文件写入被拒绝而失败，目标发送次数为 0；正式桌面聊天读取也仍报错。此项恢复终端启动，聊天指挥与原生鼠标控制尚未恢复。[原因、对照实测与回滚](docs/mxc-startup-failure.md)。

**权限与错误记录更新：** Dot 在自身工作目录成功写入请求，但后续目标回合中断；失败回执已保存，未重发。应用保存的完全访问与自动续跑的实际只读权限曾不一致，现已明确设置官方默认权限配置档并验证加载，自动续跑仍待验收。只读查询工具新增受限、过滤凭据的启动错误记录；9 项测试与真实本机元数据读取通过。云端 HTTP 403 和 Dot 原生控制仍未恢复。[实际权限、诊断修复及剩余验收](docs/permissions-and-diagnostics-2026-10-11.md)。

## 快速判断

**代理预检与备用入口：** 官方系统代理功能候选未证明恢复，已精确回滚。单域名限时透传曾通过一次 TLS，但后续严格复查失败；UAC 验收在预检阶段停止，hosts 未改。新本地聊天用自己的工具通过窗口枚举、终端和聊天读取，原生 Dot 仍未恢复。[实际结果与验收边界](docs/runtime-proxy-preflight.md)。

**运行中连接排查：** 用户要求保留登录和任务，后续不再以重新登录或重启作为前置步骤。匿名请求对照与安装版静态检查发现可能不同的云端 WebSocket 路由，具体拒绝原因及运行中修复仍未确认。[新增网络证据与检修范围](docs/runtime-network-routing.md)。

**运行中设置核对：** 实际页面中完整访问、允许连接、任意应用控制均已开启。云端恢复对话仍报 app-server 不可用，日志记录握手 403 和持续自动重连。新增只读日志分类工具，14 项测试及当前日志实测通过；这项工具改善诊断，尚未恢复月儿控制。[页面与日志核对](docs/runtime-network-routing.md#运行中页面与日志核对)。

**TLS 与隧道更新：** 已配置代理对 ChatGPT 网页返回域名不匹配的证书；无显式代理仍经过现有 WARP。临时域名路径测试没有恢复服务，系统代理和 WARP 测试项均已回滚。新增严格验证证书、仅执行 TLS 握手的只读工具，全仓 20 项测试通过；桌面云端 403 与 Dot 控制仍未解决。[实测、回滚及推断边界](docs/tls-and-tunnel-routing.md)。

**传输与路由复查：** 临时请求 WARP HTTP/2 传输未建立可验证的连接，已撤销测试选项。FlClash 对应版本源码会重写桌面 TUN 路由范围，因此未启用未验证的限定路由方案；检查配置已逐字节恢复。最终 WARP 网络健康，桌面云端仍返回新的 HTTP 403，Dot 控制尚未恢复。[试验结果与恢复核对](docs/tls-and-tunnel-routing.md#后续传输试验与限定路由检查)。

**本地插件启动修复：** 新查到两个私人插件的 MCP 配置引用源码仓库目录，安装后入口不存在。备份后修正两份安装配置的程序及入口路径，保持任务工作目录；三个服务在另一工作目录通过初始化与工具列表检查。私人记忆技能的 263 项测试及包检查也通过。这些结果不代表桌面已有工具上下文已经重新加载，月儿云端的新握手仍为 HTTP 403。[路径修复、验证范围与回滚](docs/plugin-entry-paths.md)。

| 现象 | 先检查什么 | 本案例结果 |
| --- | --- | --- |
| 电脑离线或未授权 | Dot 自己的电脑连接权限与在线上报通道 | 早期连接已通过；后续在线通道反复返回 HTTP 403 |
| “已连接”但恢复对话报 app-server 不可用 | 最新 durable 云端握手事件及时间，避免沿用缓存标签 | 完整访问和应用控制已开启，云端握手仍为 403 |
| 命令尚未创建就失败 | Windows 沙盒初始化日志 | elevated 初始化触发文件占用错误 32 |
| MXC launcher 报 0x80070020 | 实际沙盒选择、桌面 prefer_mxc、系统 requirements | 限制 MXC 后独立 CLI 与 Dot 自己的终端检查通过 |
| 命令能启动，写指定文件被拒绝 | 该任务的目录权限、正式授权机制 | 与初始化故障分开处理 |
| cloud_threads_read 报 placement 格式错误 | 云端接口与目标本机聊天兼容性 | 本机官方接口可读取，云端路径仍失败 |
| 启动调用超时 | 目标实际回合、回执文件 | 请求后来执行成功，不能直接重发 |
| Transport closed 或服务突然退出 | 同时段服务日志、Windows 事件 2004、提交内存上限 | 同日查到内存分配失败；与沙盒初始化分开 |
| proxy 报 os error 10050 | 本机代理控制入口是否可用 | 本案例默认 stdio 可读，旧 socket 失败 |

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

- `scripts/probe_local_task.py`：通过安装版官方 app-server 读取一个指定聊天的元数据；可用 `--latest-turn` 读取最新回合 ID/状态。服务提前退出时保留退出码及最多 2000 字符的错误摘要，丢弃含凭据标记的整行。没有聊天内容、不恢复任务、不发送指令。报告可能含本机路径和聊天名称，保持本地。
- `scripts/inspect_cloud_connection.py`：只读检查当天及前一天 UTC 日志，最多 12 个文件、每个尾部 256 KiB。区分本机错误、近期云端 403、旧事件和新 ready 状态；只输出状态、时间及计数，没有原始日志或标识。不连接服务器、不刷新登录、不改设置；ready 仍需实际任务验收。
- `scripts/probe_tls_routes.py`：对两个固定的公开域名比较无显式代理与现有本机代理的 TLS 证书验证结果。使用默认信任和域名验证；不读取登录、不发送服务端应用请求、不改变网络配置。默认本机代理端口为 10808，可用参数选择已配置的端口。任一路径未验证通过时退出码为 1，报告仍可用于诊断。
- `scripts/bounded_socks_relay.py`：实验性固定目标、回环监听的限时透传，显式选择 HTTP CONNECT 或 SOCKS5，最长运行 180 秒。它不改 hosts、不解密 TLS、不重放消息；通过合成测试和一次 TLS 检查，不代表桌面或 Dot 控制已经验收。[范围与实测](docs/runtime-proxy-preflight.md)。
- `scripts/resolve_codex.py`：Windows 上自动查找桌面安装的 CLI，避免更新后仍引用已删除的版本目录；也可用 `--codex` 明确指定路径。此工具不更改桌面应用本身。
- `scripts/verify_receipts.py`：离线比较“发送方结果”和“目标实际回执”，要求回合完成、目标和回合一致、回复完全匹配。
- `examples/`：合成的协议与回执样例；**不是新的实测结果**。
- `evidence/case-summary.redacted.json`：从原始本机证据核对后生成的脱敏事实摘要；原始记录不在仓库内。
- `MANIFEST.sha256`：发布源文件清单及校验值。

```powershell
python scripts/probe_local_task.py --help
python scripts/inspect_cloud_connection.py --output ./local-reports/cloud-state.json
python scripts/probe_tls_routes.py --proxy-port 10808 --output ./local-reports/tls-state.json
python scripts/verify_receipts.py examples/sender-result.json examples/target-receipt.json
python -m unittest discover -s tests -v
```

日志检查示例要求先准备 `local-reports` 目录，报告路径必须是新文件。其他系统可用 `--log-root` 明确指定桌面日志根目录；该目录须包含 UTC `YYYY/MM/DD` 子目录。

下载完整 ZIP 请打开 [Releases](https://github.com/JMET04/codex-dot-windows-troubleshooting/releases)。

资料反映一个环境的一次排查。按自己的错误与版本核对，不把“已连接”“工具存在”“回合完成”单独当作工作成功的证据。
