---
tags:
  - homelab
  - 排障
publish: true
---
### 1. **编辑配置文件并取消注释**

```bash
sudo nano /etc/ssh/sshd_config
```

找到以下行，去掉`#`并修改为：

```bash
PermitRootLogin yes  # 改为yes允许密码登录
# 或
# PermitRootLogin prohibit-password  # 保持这个值但取消注释（只能密钥登录）
```

### 2. **同时确保密码认证已启用**

找到以下行并取消注释：

```bash
#PasswordAuthentication yes
```

改为：

```bash
PasswordAuthentication yes
```

### 3. **完整修改后的配置示例**

```bash
#LoginGraceTime 2m
PermitRootLogin yes
#StrictModes yes
#MaxAuthTries 6
#MaxSessions 10
PasswordAuthentication yes
```

### 4. **重启SSH服务**

```bash
sudo systemctl restart sshd
# 或
sudo service ssh restart
```

### 5. **如果不想修改配置文件，可用临时方案**

```bash
# 添加临时配置（重启后会失效）
sudo /usr/sbin/sshd -o "PermitRootLogin yes" -o "PasswordAuthentication yes" -p 22
```

### 6. **单行命令快速修改**

```bash
# 使用sed快速修改
sudo sed -i 's/^#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
sudo sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

## 检查修改是否生效：

```bash
# 查看实际生效的配置
sudo sshd -T | grep -E "permitrootlogin|passwordauthentication"
```

## 如果仍然无法登录：


1. **检查防火墙**：

   ```bash
   sudo ufw status
   sudo iptables -L -n
   ```
2. **检查SELinux**：

   ```bash
   sudo getenforce
   # 临时关闭
   sudo setenforce 0
   ```
3. **查看SSH日志**：

   ```bash
   sudo tail -f /var/log/auth.log
   # 或
   sudo journalctl -u sshd -f
   ```

修改后，应该可以使用`ssh root@IP`并输入密码登录了