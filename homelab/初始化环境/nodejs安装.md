---
publish: true
---
**方式一：NodeSource（推荐，系统级安装）**

NodeSource 支持 Node.js v20.x、v22.x、v24.x。

```bash
apt update && apt upgrade -y && apt install -y curl

# 导入 GPG 密钥
mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg

# 添加仓库（NODE_MAJOR 改成你要的版本号）
NODE_MAJOR=24
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list

apt update && apt install -y nodejs
```


---

**方式二：fnm（Node.js 官网推荐的版本管理器）**

Node.js 官网的包管理器页面推荐使用 fnm，官方安装脚本如下：

```bash
# 下载并安装 fnm：
curl -o- https://fnm.vercel.app/install | bash

# 下载并安装 Node.js：
fnm install 24

# 验证 Node.js 版本：
node -v # Should print "v24.14.0".

# 验证 npm 版本：
npm -v # Should print "11.9.0".
```

注意：fnm 官方就是用 `fnm.vercel.app` 这个域名托管安装脚本的


---

**总结：**

* LXC 容器跑服务 → 用**方式一**，系统级安装，干净
* 需要多版本切换 → 用**方式二** fnm

### 更新

**方式一（NodeSource apt）**

```bash
apt update && apt upgrade -y
```

和更新其他系统包一样，会自动升级到该大版本的最新版（比如 22.x 的最新补丁）。

如果要跨大版本升级（比如 22 → 24），重新走一遍添加仓库的流程，覆盖 `/etc/apt/sources.list.d/nodesource.list` 里的版本号即可。


---

**方式二（fnm）**

```bash
fnm install 22      # 安装该大版本最新
fnm use 22
fnm default 22      # 设为默认
```

跨版本同理，把版本号换掉就行。旧版本不会自动删除，用 `fnm uninstall <version>` 手动清理。