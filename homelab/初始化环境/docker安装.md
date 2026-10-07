---
publish: true
---
### 配置仓库

```bash
# Add Docker's official GPG key:
sudo apt update
sudo apt install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
```

### 安装

```javascript
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```


---

### 卸载

```javascript
apt purge docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-ce-rootless-extras
rm -rf /var/lib/docker /var/lib/containerd
rm /etc/apt/sources.list.d/docker.sources /etc/apt/keyrings/docker.asc
```


**⚠️ LXC 容器特别注意：**

LXC 容器默认不支持运行 Docker，因为 Docker 需要内核命名空间和 cgroup 权限。你需要在 Proxmox 的 LXC 配置里开启特权容器，或者手动在 `/etc/pve/lxc/<id>.conf` 添加：

```
features: keyctl=1,nesting=1
```

否则 Docker 服务会启动失败。


---

**更新方式：** 和 Node 一样，`apt update && apt upgrade -y` 即可。