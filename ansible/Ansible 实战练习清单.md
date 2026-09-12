---
publish: true
---
	## 说明

按顺序做，每一关都是为了用上前面笔记里的某个知识点。做完打勾，卡住了回对应笔记翻。

这份清单经过一轮修正：原版漏了**幂等性**和 **Handler** 两个 Ansible 最核心的概念，顺序也调整为更符合实际学习曲线的路径：

```
1 Inventory/SSH → 2 Ad-hoc/Modules/Facts → 3 Playbook → 4 幂等性
→ 5 Variables/Jinja2 → 6 when/loop/register → 7 Handler → 8 Role → 9 综合实战
```

## 第一关：Inventory 和连通性

- [x] 给你的 homelab 建一份 YAML 格式 Inventory，至少分两个组（比如 `docker_hosts`、`pi_hosts`），每台主机写清 `ansible_host`
- [x] `ansible-inventory --graph` 检查分组结构对不对
- [x] `ansible all -m ping` 测通所有节点；连不上就走一遍 [[linux/网络排障/网络故障排查 Runbook.md]]
- [x] 故意在 Inventory 里写错一个 IP，观察 `ping` 模块报错信息长什么样

对应笔记：[[ansible/Ansible Inventory.md]]

## 第二关：临时命令玩转模块

- [x] 用 `ansible all -m setup` 看看能收集到哪些 Facts，找一个你觉得有用的字段（比如 `ansible_distribution`）
- [x] 用 `command` 模块跑 `uptime`，再用 `shell` 模块跑一个带管道的命令，体会两者的区别
- [x] 用 `-C` 检查模式模拟一次 `copy` 模块操作，确认不会真的改动文件
- [x] 用 `ansible-doc -l | grep` 找一个你没用过的模块（比如 `cron` 或 `lineinfile`），看完文档后用临时命令跑一次
- [x] 小练习：用 `shell: df -h` + `register` + `debug` 打印所有节点的磁盘使用率——这是练 `register`/`debug`/Facts 用法的，**不要把它当成长期巡检手段**，持续性主机监控该交给 Prometheus/Grafana，Ansible 干这个活是杀鸡用牛刀，也不是它的强项

对应笔记：[[ansible/Ansible 模块.md]]、[[ansible/Ansible Doc.md]]、[[ansible/Ansible CLI.md]]

## 第三关：第一个 Playbook

- [x] 写一个最简单的 playbook：确保 `htop`（或任意小工具）在所有节点上装好
- [x] 加两个 tag（比如 `install`、`verify`），分别用 `-t` 跑一次，体会标签过滤
- [x] 执行前先 `--syntax-check`，再 `--check -D` 预演，确认无误后再真跑
- [x] 写一个多 Play 的 playbook，对 `docker_hosts` 和 `ubuntu` 做不同的事情

对应笔记：[[ansible/Playbook/Ansible Playbook 编写.md]]、[[ansible/Playbook/Ansible Playbook.md]]

## 第四关：幂等性（核心关卡，别跳过）

这是 Ansible 和"写个 shell 脚本批量执行"的本质区别所在，也是这套清单原版最大的缺口。

- [x] 连续执行两次第三关装 `htop` 的 playbook，观察第一次 `changed=1`，第二次 `changed=0`
- [x] 用 `copy`/`template`/`file` 模块修改一个配置文件，重复执行确认不会重复产生 `changed`
- [x] 写一个 `shell`/`command` 任务（比如 `shell: echo hello`），观察为什么它**每次执行都显示 changed**——因为 Ansible 不知道这条命令有没有真的改变系统状态，只能假设"跑了就算变了"
- [x] 用 `changed_when` 手动修正上面这个任务的 changed 判断逻辑（比如根据命令输出内容判断是否真的发生了变化）
- [x] **关键练习**：找一个你写过的 `shell` 任务，比如 `shell: useradd foo`，改写成对应的声明式模块：
  ```yaml
  # ❌ 之前的写法
  - shell: useradd foo

  # ✓ 改写后
  - ansible.builtin.user:
      name: foo
      state: present
  ```
  跑两次，体会两种写法在幂等性上的天壤之别

记住这条原则：**能用 Module，就不要用 shell/command**。后者是 Ansible 里的"逃生舱"，不是默认选项。

对应笔记：[[ansible/Playbook/Ansible Playbook 编写.md]] 里的幂等性小节

## 第五关：变量和模板

- [x] 用 `template` 模块给所有节点分发一份 `/etc/motd`，内容里用 Jinja2 插入每台机器的 `ansible_hostname` 和 `ansible_distribution`
- [x] 在 Inventory 或 `host_vars/` 里给不同主机设置不同变量，playbook 里引用它
- [x] 故意在 YAML 里漏写引号（比如 `port: {{ my_port }}`），观察报错，验证笔记里提到的那个坑是真的

对应笔记：[[ansible/Playbook/Ansible Templating.md]]

## 第六关：条件、循环、register

- [x] 写一个 `when` 条件任务：只在 `ansible_distribution == "Ubuntu"` 时执行某个安装
- [x] 写一个 `loop` 任务：一次性安装一个包列表（比如 `[curl, git, vim]`），而不是写三个重复任务
- [x] 用 `register` 捕获一个任务的执行结果，在后续任务里用 `when` 判断这个结果做条件分支
- [x] 卡壳的地方，把对应官方文档链接甩过来，展开成正式笔记

对应笔记：[[ansible/Playbook/Ansible Conditionals.md]]、[[ansible/Playbook/Ansible Loops.md]]、[[ansible/Playbook/Ansible Register.md]]（三个都已从索引展开成正式笔记）

## 第七关：Handler

这个和第四关的幂等性是一体两面：**配置没有发生变化，就不应该重启服务**。

- [ ] 写一个 playbook：用 `template` 渲染 nginx（或任意有配置文件的服务）的配置文件
- [ ] 给这个 `template` 任务加上 `notify: restart nginx`
- [ ] 在 `handlers:` 里定义 `restart nginx`，对应 `service`/`systemd` 模块的重启动作
- [ ] 连续跑两次：第一次配置文件变化触发重启；第二次配置没变化，观察 handler **完全不会被触发**
- [ ] 故意手动改一个字符再跑，确认 handler 又被触发了——理解 `notify` 是靠上游任务的 `changed` 状态驱动的，不是无脑每次都执行

对应笔记：[[ansible/Playbook/Ansible Playbook 进阶主题索引.md]]

## 第八关：Role 化重构

- [ ] 挑一个你在第三～七关写的 playbook 逻辑，用 `ansible-galaxy role init` 拆成一个角色
- [ ] 把平铺的 tasks 迁移进角色的 `tasks/main.yml`，模板迁移进 `templates/`，handler 迁移进 `handlers/main.yml`
- [ ] 在新的 playbook 里通过 `roles:` 引用这个角色，确认效果和之前一样

对应笔记：[[ansible/Ansible Galaxy.md]]

## 第九关：Homelab 综合实战 —— 真正的 Docker Host

这一关不是练习题，是拿真实的 Docker Host 开刀，产出一份你以后重装机器还能直接跑的 Infrastructure as Code。

> 这一关实际踩了不少坑（DEB822 仓库格式、Architectures 字段、cache_valid_time 反模式、-C 检查模式误导、fnm 实际安装路径），完整排障过程见 [[Docker & fnm部署踩坑记录]]。

**目标**：一台裸 Ubuntu VM，跑一个 `docker-host.yml`，跑完自动变成生产可用的 Docker 节点。

```
配置软件源
    ↓
安装 Docker
    ↓
配置 daemon.json
    ↓
创建 docker 用户组，添加指定用户
    ↓
enable + start docker 服务
    ↓
验证 docker info
    ↓
部署 node_exporter（供 Prometheus 采集，不是自己写巡检脚本）
    ↓
基础工具安装（htop、curl、vim 等）
    ↓
配置防火墙规则（对应 [[linux/防火墙/防火墙总览.md]]）
```

- [x] 按上面的流程写完整的 `docker-host.yml`
- [x] 全程使用声明式模块（`apt`/`apt_repository`、`get_url`/`shell` 装 Docker、`template` 写 `daemon.json`、`group`/`user`、`service`）而不是一路 `shell` 糊过去
- [x] 第一次执行，观察 `changed=N`（N 应该是个不小的数字，因为要做的事情很多）
- [x] 立刻重新执行一次，确认 `changed=0`——这是检验这份 playbook 写得"够不够 Ansible"的试金石
- [x] **终极验证**：把这台 VM 恢复到跑 playbook 之前的快照，重新执行 `docker-host.yml`，确认能完整从裸机自动恢复出一个可用的 Docker Host

这份 playbook 做完之后，是你 Homelab 里第一份真正意义上的 Infrastructure as Code，价值远超任何一道单独的练习题。

## 完成之后

如果这九关做下来没有大问题，说明 Ansible 的日常使用和核心思维模型（Desired State + Idempotency）已经过关了。剩下的（Vault、Pull、模块开发）保持"知识存档，按需查阅"的状态就够，不需要专门刷。

顺手看看 [[ansible/踩坑记录/Ansible pipx 安装踩坑记录.md]]，当时踩的坑里有没有能被这份 `docker-host.yml` 顺带自动化掉的手动步骤。
