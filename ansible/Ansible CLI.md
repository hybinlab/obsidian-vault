---
publish: true
---
## ansible 临时命令常用参数

语法：`ansible 受管主机节点 -m 模块名称 [-a 模块参数]`

### 连接和用户相关

|参数|作用|
|---|---|
|-i|指定主机清单文件路径|
|-u|指定远程连接用户名|
|-k|手动输入 SSH 协议密码|
|-b / --become|提权执行（sudo），需搭配 `-K` 输入提权密码|
|-K|提示输入提权密码|
|-T|设置 SSH 协议连接超时时间（秒）|

### 模块相关

|参数|作用|
|---|---|
|-m|指定要使用的模块名|
|-M|指定要使用的模块路径|
|-a|设置传递给模块的参数|

### 执行控制

|参数|作用|
|---|---|
|-C / --check|检查模式，只预演不实际执行（dry-run）|
|-D|显示文件变更的 diff 详情|
|-f|并发进程数（默认 5）|
|-B|异步执行，设定超时时间（秒）|
|-P|异步轮询间隔（秒），需搭配 `-B`|
|-l / --limit|进一步限定目标主机范围（子集）|

### 变量和调试

|参数|作用|
|---|---|
|-e / --extra-vars|传递额外变量，可用 JSON 或 `key=value` 形式|
|-v|调试输出，显示任务执行细节|
|-vv|更详细的调试输出|
|-vvv|更更详细的调试输出（包括 SSH 连接信息）|
|-vvvv|最详细的调试输出（包括内部插件调用）|

### 其他

|参数|作用|
|---|---|
|-S|使用 su 命令而非 sudo|
|--version|查看 Ansible 版本信息|
|-h|显示帮助信息|

> 大多数情况下 `-m` 和 `-a` 会同时出现，只有极简单功能的模块才不需要额外参数。
> 
> 常见组合：
> - `ansible all -m ping` — 测试连通性
> - `ansible webservers -m copy -a "src=file.txt dest=/tmp/" -u admin -k` — 复制文件+指定用户+手动输密码
> - `ansible all -m command -a "systemctl restart nginx" -b -K` — 执行需要提权的命令
> - `ansible all -m setup -v` — 收集系统信息并显示详细输出

## 检查模式（Check Mode）

检查模式下 Ansible **不会执行任何改动**，只会打印命令效果的预演结果，用于验证任务逻辑是否正确。常用于危险操作前的"排练"。

```bash
# 示例：检查是否会创建 /root/bar.txt 文件（但实际不会创建）
ansible all -m copy -a "content=foo dest=/root/bar.txt" -C
```

输出会显示 `changed: true`，表示若真实执行则会做改动。

**局限性**：
- 某些模块不支持检查模式（模块文档会标注 `supports_check_mode: false`）
- 获取文件内容的模块（如 `command`、`shell`）在检查模式下仍会执行，因为它们本身不修改系统
- 建议搭配 Playbook 中的 `check_mode: yes` 设置，或使用 `--diff` 参数看变更细节

```bash
# 结合 --diff 看具体哪些内容会改变
ansible all -m lineinfile -a "path=/etc/hosts line='192.168.1.1 example.com'" -C --diff
```

## 测试节点连通性

使用 `ping` 模块（非 ICMP，而是测试 SSH 能否连接并执行 Python）：

```bash
# 测试所有受管节点
ansible all -m ping

# 测试指定组
ansible prod -m ping

# 测试单个主机
ansible 192.168.10.22 -m ping
```

成功输出示例：

```
192.168.10.22 | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

- 首次连接若未关闭指纹验证（`host_key_checking`），会因交互确认而卡住/失败，需提前配置 `ansible.cfg` 或手动 `ssh` 一次建立信任
- 若受管节点未配置密钥登录，需加 `-k` 手动输入密码，或配合 `-u 用户名` 指定连接用户
- `ping` 模块要求受管节点已安装 Python；若只想测试**网络层**是否可达（不依赖 Python），可用 `command`/`shell` 模块跑系统 ping：
  ```bash
  ansible all -m command -a "ping -c 2 目标IP"
  ```
