---
tags:
  - ansible
  - 排障
publish: true
---
# Docker & fnm 部署踩坑记录

> 日期：2026-09-08 背景：[[ansible/Ansible 实战练习清单.md]] 第九关，写 `docker-host.yml` 把裸 Ubuntu 24.04（noble）自动配置成 Docker Host 的过程中，实际踩到的坑。

---

## 问题一：`apt_repository` vs `copy` 写仓库

**现象**：一开始用 `ansible.builtin.apt_repository` 模块生成传统的一行式 `deb [arch=...] url suite component` 格式，写进 `.list` 文件。

**原因**：Docker 官方文档已经改成 **DEB822 格式**（`.sources` 文件，`Types:`/`URIs:`/`Signed-By:` 这种 key-value 结构）。`apt_repository` 模块是为传统一行式格式设计的，生成不了 `.sources` 文件。旧格式目前 apt 仍然支持，不算错误，但不是官方当前推荐做法。

**解决**：改用 `copy`/`template` 模块直接写 `.sources` 文件内容，跟官方文档格式保持一致。

```yaml
- name: 添加 Docker 仓库（DEB822 格式）
  ansible.builtin.copy:
    dest: /etc/apt/sources.list.d/docker.sources
    content: |
      Types: deb
      URIs: https://download.docker.com/linux/ubuntu
      Suites: {{ ansible_distribution_release }}
      Components: stable
      Signed-By: /etc/apt/keyrings/docker.asc
      Architectures: {{ 'amd64' if ansible_architecture == 'x86_64' else 'arm64' }}
    mode: '0644'
```

---

## 问题二：`Architectures` 字段必须显式声明

**现象**：写好 `.sources` 文件后，"安装 Docker Engine" 报错 `No package matching 'docker-ce' is available`。

**原因**：传统一行式 `deb [arch=xxx] ...` 格式里，如果不写 `arch=`，apt 会按系统默认架构自动处理。但 **DEB822 格式不会自动推断架构**，不显式写 `Architectures:` 字段，apt 解析这个仓库源时可能无法正确匹配到对应架构的包。

**排查过程**：这个坑排查耗时最长，中间还错误怀疑过发行版代号（`Suites:` 用 `noble` 是否被 Docker 官方仓库支持——排查后确认 noble 是 2024 年发布的 LTS，早就支持，不是这个原因）。

**解决**：显式加上 `Architectures:` 字段。

---

## 问题三：`cache_valid_time` 在「必须强制更新」场景是反模式

**现象**：加了 `Architectures` 字段后仍然报同样的错。仔细看发现"刷新 apt 缓存"这个 task 用了 `cache_valid_time: 3600`。

**原因**：`cache_valid_time` 的语义是"如果距上次更新不到 N 秒，跳过这次更新，直接用旧缓存"，是**基于时间戳**判断，不知道"仓库内容有没有变化"。playbook 最前面的"更新 apt 缓存"和"添加仓库后刷新缓存"这两个 task 之间只隔了几秒钟，第二次刷新被 `cache_valid_time` 判定为"缓存还新鲜"，直接跳过，没有真正执行 `apt update`——仓库文件写进去了，但缓存里依然没有 Docker 仓库的内容。

**解决**：凡是"刚做了会影响仓库内容的改动，必须确保缓存是最新的"场景，一律不加 `cache_valid_time`，无条件强制刷新：

```yaml
- name: 刷新 apt 缓存（强制，添加 Docker 仓库后）
  ansible.builtin.apt:
    update_cache: yes    # 不加 cache_valid_time
```

**真正的元凶（复盘补充）**：改完这两处之后还是报同样的错，最后发现是因为一直在用 `-C`（检查模式）反复测试——`copy` 模块在检查模式下只是模拟"changed"，并不会真的把 `.sources` 文件写到磁盤。这意味着后面无论怎么改 `Architectures`/`cache_valid_time`，仓库文件在磁盤上始终不存在，apt 缓存里自然永远没有 Docker 仓库的内容，报错完全不变。**教训：调试报错时先确认是不是一直带着 `-C` 在跑**，这个坑比前两个更隐蔽，因为它会让任何后续的"修复"都显得没有生效。

---

## 问题四：fnm 装在 `~/.local/share/fnm/`，不是脚本暗示的 `~/.fnm/`

**现象**：`ansible.builtin.shell` 执行 `curl -fsSL https://fnm.vercel.app/install | bash` 后显示 `changed`（说明真的执行了），但下一个 task 验证 `{{ ansible_env.HOME }}/.fnm/fnm --version` 时报 `No such file or directory`。

**排查过程**：一开始怀疑是 `become: yes` 导致 `ansible_env.HOME` 和实际安装用户不一致（排查后确认因为 `become` 是 Play 级别生效，Gathering Facts 阶段也会以提权用户身份收集，所以 `ansible_env.HOME` 和实际执行环境是一致的，不是这个问题）；又怀疑是 `curl | bash` 管道里 `curl` 静默失败导致 `bash` 执行了空内容（用户确认手动 `curl` 没问题，排除）。最后用 `find` 在目标机器上实际搜索，才发现文件根本没装到 `~/.fnm/`。

**原因**：`fnm.vercel.app/install` 这个官方安装脚本实际默认把 fnm 装到 `~/.local/share/fnm/`（遵循 XDG Base Directory 规范），不是很多旧教程里写的 `~/.fnm/`。**这种"约定俗成"的路径经常和实际不符，靠记忆/猜测容易踩坑，必须实测确认。**

**解决**：playbook 里所有引用 fnm 路径的地方，统一改成 `~/.local/share/fnm/`；并且给关键的 shell/command task 加上 `register` + `debug` 输出，下次遇到类似问题能直接看到第一手执行日志，不用靠层层排除法倒推。

---

## 总结：这次调试暴露的排障方法论

1. **先确认是不是在用 `-C`**：检查模式下 `copy`/`template` 等写文件的模块不会真的执行，任何"改了但报错没变"的诡异现象，第一时间怀疑这个
2. **管道命令注意静默失败风险**：`curl | bash` 这类写法，`curl` 失败不代表整个命令会报错，必要时用 `set -o pipefail` 兜底
3. **不要相信记忆中的路径，用 `find` 实测**：安装脚本的实际行为可能和文档/记忆不一致，尤其是版本升级后
4. **给关键的 `shell`/`command` task 都加上 `register` + `debug`**：调试的时候能看到第一手输出，不用靠"下一个 task 失败了"倒推上一个 task 发生了什么
5. **`cache_valid_time` 这类"性能优化参数"和"强制生效"的需求是冲突的**：默认值该用就用，需要强制生效的场景不要偷懒加优化参数

## 相关笔记

- [[ansible/Ansible 实战练习清单.md]] — 第九关，这份踩坑记录对应的练习
- [[ansible/Playbook/Ansible Playbook 编写.md]] — 幂等性、state 概念
- [[ansible/Ansible CLI.md]] — `-C` 检查模式的说明
