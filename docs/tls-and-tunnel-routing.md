# 网页证书错误与现有 WARP 隧道

记录日期：2026-10-11。当前 Dot 的云端连接和电脑控制仍未恢复。这一轮发现了可复现的网页 TLS 故障，但没有证明它就是桌面 WebSocket 403 的根因。

## 严格 TLS 对照

01:04 UTC 使用系统默认信任链与域名验证，分别对两个公开域名进行 TLS 握手；本机代理路径先执行不带认证的 HTTP CONNECT。没有读取登录凭据、发送浏览器会话或在 TLS 握手后发送应用请求。

| 域名 | 无显式代理 | 已配置本机代理 |
| --- | --- | --- |
| chatgpt.com | TLS 验证通过 | 域名不匹配，验证拒绝 |
| codex-cloud-backend.chatgpt.com | TLS 验证通过 | TLS 验证通过 |

另外一次保留验证的证书回调检查确认：被拒绝的证书属于无关域名。该回调只接受无验证错误的连接；没有关闭证书验证或继续向错误站点发送请求。实际无关域名不进入公开证据。

官方网页入口当时在原路径下报告 `ERR_CERT_COMMON_NAME_INVALID`。后台域名当时在两条路径上都通过 TLS，因此不能把网页域名的证书故障直接解释为后台的 HTTP 403。

01:24 UTC 在试验配置回滚后运行新只读工具：网页域名两条路径均通过 TLS，后台无显式代理通过，而本机代理路径超时。随后在原配置下重新加载网页，主页成功加载，但内置浏览器没有登录会话。结果说明故障具有间歇性，不能把首轮证书错配描述为始终失败，也不能据此证明桌面云端或 Dot 会话已恢复。

## 无显式代理并不等于没有隧道

网页测试和现有客户端的只读状态证实，本机使用现有 Cloudflare WARP。客户端当时报告 `Connected / Network: unstable`，模式为 `warp`，使用 MASQUE，域名分流模式为 exclude。

WARP 的流量模式会让设备流量经过隧道；域名分流实际影响解析出的 IP，可能同时影响共享这些 IP 的其他域名。DNS 处理与 IP 分流也不是同一项配置。[Cloudflare 模式说明](https://developers.cloudflare.com/warp-client/warp-modes/)，[官方分流排查说明](https://developers.cloudflare.com/cloudflare-one/troubleshooting/warp-client/)。

本案例两个目标域名当时共享全部解析地址。因此，即使只设置一个域名，也不能声称仅影响该域名的单个网页。此前“无显式代理”测试只能描述客户端参数，不能据此断言最终网络出口。

## 临时路径试验与回滚

在保存原值后，临时向 Windows 系统代理例外添加准确的 `chatgpt.com`，并调用官方设置变更通知。网页不再出现证书错误，但官方页面返回“Unable to load site”，没有进入 Dot。随后将这项例外恢复为原值并回读确认，没有保留无效的试验配置。[Windows 代理配置说明](https://learn.microsoft.com/en-us/windows/win32/wininet/enabling-internet-functionality)，[设置变更通知](https://learn.microsoft.com/en-us/windows/win32/wininet/option-flags)。

另一次使用现有 WARP 客户端的正式命令进行临时域名排除测试，未能建立有效 HTTPS 请求。测试域名已移除，最终域名排除列表数量与原值一致，原工作模式保留。没有退出登录、重启 Codex 或取消用户任务。

第一次回读检查使用了错误的 CLI 字段名称，误报了恢复结果。后续按实际返回的 `value` 字段重新检查，完成移除并确认恢复，修正记录保留本地。退出码 0 和一次未匹配的读取都不能代替设置回读；不得沿用第一次的错误结论。

试验结束后的新日志仍记录云端握手 403。证书错误、网络不稳定、请求被拒绝可以分别确认，但目前不能证明同一个根因，也没有恢复电脑控制。原始配置备份、证书和网页 IP 保留本地；公开摘要见 [tls-routing.redacted.json](../evidence/tls-routing.redacted.json)。

## 只读检查工具

新增 [probe_tls_routes.py](../scripts/probe_tls_routes.py)，仅允许上述两个公开目标和回环地址代理。工具不读取系统设置或账户，不自动切换代理、WARP 或路由，不输出原始响应头、证书或异常消息。它始终使用默认 TLS 信任与域名验证；证书拒绝后不会尝试降低验证要求。

代理 CONNECT 响应最多读取 8192 字节。每条路径的套接字操作有截止时间；系统 DNS 解析使用操作系统自身的超时，因此不能把参数当成整个程序的绝对运行时限。报告文件必须是新文件；存在任何未通过 TLS 验证的路径时退出码为 1。全部 TLS 通过也只证明证书握手，不证明服务登录、Dot 通信或电脑控制可用。

新增测试覆盖证书拒绝后不重试、默认信任和域名验证、代理认证或伪造成功响应被拒绝、头部读取上限、固定目标限制和既有证据保护。全仓 20 项测试通过；原生控制尚未验收。

官方文档支持在桌面浏览器访问同一个 Dot，电脑授权不会因为切换消息入口而撤销。本案例网页入口未能加载，因此尚不能把它作为已恢复的通道。[Dot 的消息入口](https://learn.chatgpt.com/docs/dots/channels)，[电脑与应用授权](https://learn.chatgpt.com/docs/dots/computers-and-apps)。

## 后续传输试验与限定路由检查

现有 WARP CLI 提供 MASQUE 的 `h2-only` 传输选项。一次有回滚的对照请求返回退出码 0，但随后 30 秒内客户端保持 Connecting，未验证实际建立 HTTP/2 传输，也未恢复 Dot。撤销试验选项后，已核对保存的设置和原工作模式，客户端重新 Connected；云端握手 403 随之再次出现。不能把“接受设置命令”视为传输建立，更不能把这次结果推广为 HTTP/2 在该环境永远不可用。[Cloudflare 客户端连接与端口说明](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/deployment/firewall/)。

另检查已安装的 FlClash `0.8.91+2025122201`，拟将后台的公开解析地址单独路由至现有回环代理。当前 Mihomo 文档支持使用 `route-address` 限制路由网段，但上层客户端可能重写这些选项。[Mihomo TUN 配置](https://wiki.metacubex.one/config/inbound/tun/)。

FlClash 对应 `v0.8.91` 标签的源码中，`Tun.getRealTun` 的桌面分支将 `autoRoute` 设为 true，并将 `routeAddress` 清空；本机界面仅提供虚拟网卡开关和协议栈，没有显示限定网段设置。源码检查不等于开启后的运行验证，也不能据此声称安装包的每个分支都已检查。因为尚无证据保证限定范围，未开启 TUN，未将此方案描述为修复。[对应版本的桌面分支](https://github.com/chen08209/FlClash/blob/v0.8.91/lib/models/clash_config.dart#L195)。

检查前完整备份偏好文件并关闭自动联网动作；正常退出本次打开的界面及核心后，偏好文件逐字节恢复为原值，原系统代理保留。没有启用虚拟网卡或改变系统 DNS。最后复查时 WARP 报告 Connected / Network: healthy，桌面仍记录新的云端 WebSocket HTTP 403。健康的隧道不证明 Dot 握手成功，403 本身也没有给出服务端拒绝原因。脱敏记录见 [transport-and-route-scope.redacted.json](../evidence/transport-and-route-scope.redacted.json)。
