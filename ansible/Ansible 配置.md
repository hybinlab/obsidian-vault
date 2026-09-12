---
publish: true
---
## 配置文件位置

默认：`/etc/ansible/ansible.cfg`

Ansible 会按优先级读取配置文件（表16-2），自己新建的配置文件优先级最高：

|优先级|文件位置|
|---|---|
|1（最高）|`ANSIBLE_CONFIG` 环境变量指定的路径|
|2|`./ansible.cfg`（当前目录）|
|3|`~/.ansible.cfg`（用户家目录）|
|4（最低）|`/etc/ansible/ansible.cfg`（系统默认）|

## 生成配置文件（规范做法）

不需要手动从零写，用 `ansible-config` 工具生成完整默认配置模板，然后只改需要的部分：

```bash
# 生成一份带全部选项（默认注释掉）的完整配置文件
ansible-config init --disabled > /etc/ansible/ansible.cfg

# 然后用编辑器打开，只取消注释你需要改的几行
vim /etc/ansible/ansible.cfg
```

## 常用配置项

编辑完配置文件后，下面这两个是最常改的：

```ini
# 关闭 SSH 首次连接的指纹验证（免交互）
# host_key_checking = False

# 设置默认执行 Playbook 的远程用户（默认是 root）
# remote_user = root
```

> 配置修改后**立即生效**，不需要重启 Ansible 服务。

## ansible-config 子命令速查

|子命令|作用|
|---|---|
|`ansible-config view`|查看当前生效的配置文件内容|
|`ansible-config dump`|显示所有配置项的当前值（合并后的最终结果）|
|`ansible-config dump --only-changed`|只显示你改过的配置项（排查问题时很有用）|
|`ansible-config list`|列出所有可用配置项及说明|
|`ansible-config init --disabled`|生成完整默认配置模板|
|`ansible-config validate`|校验配置文件语法是否合法|

### 实战例子

```bash
# 查看当前生效的配置
ansible-config view

# 检查 host_key_checking 和 remote_user 的值
ansible-config dump | grep -E "host_key_checking|remote_user"

# 只显示被修改过的配置（排查什么被改了）
ansible-config dump --only-changed

# 校验配置文件是否合法
ansible-config validate

# 查看所有可用配置项及说明（非常长，通常配合 grep 使用）
ansible-config list | grep -i "key"
```
