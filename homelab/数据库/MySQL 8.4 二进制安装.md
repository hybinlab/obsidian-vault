---
publish: true
tags:
  - 部署
---
# MySQL 8.4 二进制安装

> 环境：Ubuntu 24.04 LTS x86_64


---

## 一、下载二进制包

前往 [MySQL Community Downloads](https://dev.mysql.com/downloads/mysql/)，选择：

* Operating System: **Linux - Generic**
* 下载 `mysql-8.4.x-linux-glibc2.28-x86_64.tar.xz`

或直接在服务器上 wget：

```bash

wget https://dev.mysql.com/get/Downloads/MySQL-8.4/mysql-8.4.11-linux-glibc2.28-x86_64.tar.xz
```


---

## 二、解压并安装

```bash

tar -xf mysql-8.4.11-linux-glibc2.28-x86_64.tar.xz -C /usr/local/
mv /usr/local/mysql-8.4.11-linux-glibc2.28-x86_64 /usr/local/mysql
```


---

## 三、创建用户和数据目录

```bash

groupadd mysql

useradd -r -g mysql -s /bin/false mysql

mkdir -p /usr/local/mysql/data

chown -R mysql:mysql /usr/local/mysql
```


---

## 四、添加到 PATH

```bash

echo 'export PATH=/usr/local/mysql/bin:$PATH' >> /etc/profile

source /etc/profile
```


---

## 五、安装依赖

Ubuntu 24.04 包名有变化，需创建符号链接：

```bash

apt install -y libaio1t64 libncurses6

ln -s /usr/lib/x86_64-linux-gnu/libaio.so.1t64 /usr/lib/x86_64-linux-gnu/libaio.so.1
```


---

## 六、初始化数据库

```bash
/usr/local/mysql/bin/mysqld --initialize --user=mysql --basedir=/usr/local/mysql --datadir=/usr/local/mysql/data
```

初始化完成后输出中会包含临时 root 密码，形如：

```
A temporary password is generated for root@localhost: xxxxxxxx
```

**务必记录此临时密码。**


---

## 七、配置 my.cnf

```bash

mkdir -p /etc/mysql

cat > /etc/mysql/my.cnf << 'EOF'
[mysqld]
basedir=/usr/local/mysql

datadir=/usr/local/mysql/data

bind-address=0.0.0.0

port=3306

EOF
```


---

## 八、配置 systemd 服务

```bash

cp /usr/local/mysql/support-files/mysql.server /etc/init.d/mysql

cat > /etc/systemd/system/mysql.service << 'EOF'
[Unit]
Description=MySQL Server

After=network.target

[Service]
Type=forking

ExecStart=/usr/local/mysql/support-files/mysql.server start

ExecStop=/usr/local/mysql/support-files/mysql.server stop

User=root

[Install]
WantedBy=multi-user.target

EOF

systemctl daemon-reload

systemctl start mysql

systemctl enable mysql
```


---

## 九、初始化安全配置

```bash

mysql -u root -p
# 输入临时密码
```

进入 MySQL 后执行：

```sql
-- 修改 root 密码
ALTER USER 'root'@'localhost' IDENTIFIED BY '你的新密码';

-- 创建远程访问用户
CREATE USER '用户名'@'%' IDENTIFIED BY '你的密码';
GRANT ALL PRIVILEGES ON *.* TO '用户名'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```


---

## 十、验证

```bash

systemctl status mysql

mysql -u root -p -e "SHOW DATABASES;"
```


---

## 注意事项

* Ubuntu 24.04 上 `libaio1` 已更名为 `libaio1t64`，需手动创建符号链接
* MySQL 8.0+ 默认使用 `caching_sha2_password` 认证，DBeaver 等客户端首次连接需开启 `allowPublicKeyRetrieval=true`，或改用旧版认证：

```sql

ALTER USER '用户名'@'%' IDENTIFIED WITH mysql_native_password BY '你的密码';
FLUSH PRIVILEGES;
```

* `bind-address=0.0.0.0` 允许所有 IP 连接，生产环境建议配合防火墙限制来源 IP

---

## 相关笔记

- [[homelab/数据库/CloudBeaver 部署与恢复手册.md]] — Web 端管理这个 MySQL 实例
- [[监控告警链路追踪/监控/mysql部署prometheus.md]] — 给这个实例接 mysqld_exporter 监控