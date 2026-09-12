---
publish: true
tags:
  - 部署
---
# PostgreSQL_的详细安装方式（全平台覆盖)

> 本文将全面、系统、深入地讲解 PostgreSQL 在 **Linux（Ubuntu/CentOS）、Windows、macOS 以及 Docker 容器** 四大主流环境下的详细安装步骤，涵盖官方仓库、包管理器、图形化安装程序、容器化部署等多种方式，并附带初始化配置、服务管理、安全加固等关键实践。

### 一、安装前准备：通用原则与注意事项

在具体操作前，需明确以下通用原则：

#### 1.1 版本选择

* **生产环境** ：建议使用 **LTS（长期支持）版本** ，如 PostgreSQL 14、15 或 16（截至 2026 年）。
* **学习/开发** ：可使用最新稳定版以体验新特性。
* 查看最新版本： <https://www.postgresql.org/download/>

#### 1.2 权限要求

* 安装过程通常需要 **root / Administrator / sudo 权限** 。
* 数据目录（ `PGDATA` ）应由专用用户（如 `postgres` ）拥有，禁止 root 运行数据库进程。

#### 1.3 端口与防火墙

* 默认端口： **5432**
* 若需远程访问，需开放防火墙端口（但首次安装建议仅本地访问）。

#### 1.4 存储路径

* 默认数据目录：
  * Linux: `/var/lib/pgsql/data` 或 `/var/lib/postgresql/{version}/main`
    * Windows: `C:\Program Files\PostgreSQL\{version}\data`
    * macOS (Homebrew): `/opt/homebrew/var/postgresql` （Apple Silicon）或 `/usr/local/var/postgres`
* 建议预留足够磁盘空间（至少 1GB 起）。


---

### 二、Linux 系统安装 PostgreSQL

Linux 发行版众多，本文以 **Ubuntu（Debian 系）** 和 **CentOS/Rocky Linux（RHEL 系）** 为代表。

#### 2.1 Ubuntu / Debian 安装（推荐使用官方 APT 仓库）

> 优势：自动更新、版本丰富、集成 systemd 服务。

##### 步骤 1：添加官方 APT 仓库

```bash
# 导入 GPG 密钥
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
# 添加仓库（以 Ubuntu 22.04 + PostgreSQL 16 为例）
echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list
# 更新包索引
sudo apt update
```

> 注意： `$(lsb_release -cs)` 自动获取发行版代号（如 jammy、focal）。若为非标准系统，可手动替换。

##### 步骤 2：安装 PostgreSQL

```bash
# 安装客户端、服务器及 contrib 扩展（含 pg_stat_statements 等）
sudo apt install postgresql-16 postgresql-client-16 postgresql-contrib-16
```

##### 步骤 3：验证安装

```bash
# 检查服务状态
sudo systemctl status postgresql@16-main
# 切换到 postgres 用户并进入 psql
sudo -u postgres psql -c "SELECT version();"
```

##### 步骤 4：初始化与配置（通常自动完成）

* 数据目录： `/var/lib/postgresql/16/main`
* 配置文件：
  * `postgresql.conf` ：主配置（监听地址、内存、日志等）
    * `pg_hba.conf` ：客户端认证配置

> **安全提示** ：默认仅允许本地 peer 认证，无需密码即可登录（通过 `sudo -u postgres` ）。


---

#### 2.2 CentOS / Rocky Linux / AlmaLinux 安装（使用官方 YUM 仓库）

> 适用于 RHEL 7/8/9 及其衍生版。

##### 步骤 1：添加官方 YUM 仓库

```bash
# 下载并安装仓库 RPM（以 Rocky Linux 9 + PG16 为例）
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
# 禁用内置 postgresql 模块（避免冲突）
sudo dnf -qy module disable postgresql
```

##### 步骤 2：安装 PostgreSQL

```bash
sudo dnf install -y postgresql16-server postgresql16-contrib
```

##### 步骤 3：初始化数据库集群

```bash
# 首次安装需手动初始化
sudo /usr/pgsql-16/bin/postgresql-16-setup initdb
# 启动并设置开机自启
sudo systemctl enable --now postgresql-16
```

##### 步骤 4：验证

```bash
sudo -u postgres psql -c "SELECT current_database();"
```

> 提示：数据目录为 `/var/lib/pgsql/16/data` 。


---

#### 2.3 从源码编译安装（高级用户）

适用于需要定制编译选项（如启用 ICU、LDAP、SSL）或最新开发版。

```bash
# 安装依赖
sudo apt install build-essential zlib1g-dev libreadline-dev flex bison libssl-dev
# 下载源码（以 16.1 为例）
wget https://ftp.postgresql.org/pub/source/v16.1/postgresql-16.1.tar.gz
tar -xzf postgresql-16.1.tar.gz
cd postgresql-16.1
# 配置编译选项
./configure --prefix=/usr/local/pgsql --with-openssl --enable-thread-safety
# 编译与安装
make -j$(nproc)
sudo make install
# 创建用户与数据目录
sudo useradd -r -s /bin/false postgres
sudo mkdir /usr/local/pgsql/data
sudo chown postgres:postgres /usr/local/pgsql/data
# 初始化
sudo -u postgres /usr/local/pgsql/bin/initdb -D /usr/local/pgsql/data
# 启动
sudo -u postgres /usr/local/pgsql/bin/pg_ctl -D /usr/local/pgsql/data start
```

> 注意：源码安装需手动管理服务、PATH 环境变量等。


---

### 三、Windows 系统安装 PostgreSQL

Windows 提供图形化安装程序，适合桌面开发。

#### 3.1 下载安装程序

* 访问 <https://www.enterprisedb.com/downloads/postgres-postgresql-downloads>
* 选择对应架构（x64 推荐）和版本（如 PostgreSQL 16.1）

#### 3.2 图形化安装步骤


1. **运行安装程序** （如 `postgresql-16.1-1-windows-x64.exe` ）
2. **选择安装目录** （默认 `C:\Program Files\PostgreSQL\16` ）
3. **设置数据目录** （默认 `C:\Program Files\PostgreSQL\16\data` ）
4. **设置超级用户密码** （务必牢记！此为 `postgres` 用户密码）
5. **选择端口** （默认 5432，若冲突可修改）
6. **选择区域（Locale）** （建议 UTF8，避免中文乱码）
7. **安装组件** ：
   * PostgreSQL Server（必需）
     * pgAdmin 4（图形化管理工具，推荐）
     * Stack Builder（附加工具，可选）
8. **开始安装** → 等待完成

#### 3.3 验证安装

* **命令行** ：

  ```
  cd "C:\Program Files\PostgreSQL\16\bin"
  psql -U postgres -h localhost
  # 输入密码后进入交互界面
  ```
* **pgAdmin 4** ：
  * 安装后自动创建快捷方式；
    * 首次启动需设置管理员邮箱和密码；
    * 添加服务器：Host `localhost` ，Port `5432` ，Username `postgres` ，Password（安装时设置）

#### 3.4 服务管理

* 服务名称： `postgresql-x64-16`
* 可通过 **Windows 服务管理器** 启停；
* 或使用命令：

  ```
  net start postgresql-x64-16
  net stop postgresql-x64-16
  ```

> **安全建议** ：生产环境中应限制远程访问，修改默认密码策略。


---

### 四、macOS 系统安装 PostgreSQL

macOS 开发者常用 Homebrew 或 Postgres.app。

#### 4.1 使用 Homebrew（推荐）

> 优势：命令行友好、易于更新、与开发工具链集成。

##### 步骤 1：安装 Homebrew（若未安装）

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

##### 步骤 2：安装 PostgreSQL

```bash
# 安装最新版
brew install postgresql@16
# 启动服务（后台常驻）
brew services start postgresql@16
```

> 提示：Apple Silicon（M1/M2）芯片路径为 `/opt/homebrew` ，Intel 为 `/usr/local` 。

##### 步骤 3：验证

```bash
# 默认无需密码（peer 认证）
psql postgres
# 或创建数据库
createdb mydb
psql mydb
```

##### 步骤 4：常用命令

```bash
brew services list                 # 查看服务状态
brew info postgresql@16           # 查看配置信息
psql -l                           # 列出数据库
```

> 数据目录： `$(brew --prefix)/var/postgresql@16`


---

#### 4.2 使用 Postgres.app（图形化首选）

> 适合不喜欢命令行的 macOS 用户。


1. 访问 <https://postgresapp.com/>
2. 下载并拖拽到 Applications 文件夹
3. 首次启动点击 "Initialize" 创建服务器
4. 自动配置 PATH，终端可直接使用 `psql`
5. 菜单栏图标可快速启停、查看日志、打开 psql

> ✨ 优点：零配置、一键启停、多版本共存、集成 pgAdmin。


---

### 五、Docker 容器化安装 PostgreSQL

容器化部署适合开发、测试、CI/CD 及微服务架构。

#### 5.1 拉取官方镜像

```bash
docker pull postgres:16
```

#### 5.2 快速启动（临时容器）

```bash
docker run --name mypg -e POSTGRES_PASSWORD=mypassword -p 5432:5432 -d postgres:16
```

* `-e POSTGRES_PASSWORD` ：设置 `postgres` 用户密码（必需）
* `-p 5432:5432` ：映射端口
* `-d` ：后台运行

#### 5.3 持久化数据（生产推荐）

```bash
# 创建卷
docker volume create pgdata
# 启动容器并挂载卷
docker run --name mypg \
-e POSTGRES_PASSWORD=mypassword \
-e POSTGRES_DB=myapp \
-v pgdata:/var/lib/postgresql/data \
-p 5432:5432 \
-d postgres:16
```

> 优势：数据不随容器销毁而丢失。

#### 5.4 自定义配置

可通过挂载配置文件覆盖默认设置：

```bash
# 创建自定义 postgresql.conf
echo "shared_preload_libraries = 'pg_stat_statements'" > ./my-postgres.conf
# 启动时挂载
docker run ... -v $(pwd)/my-postgres.conf:/etc/postgresql/postgresql.conf ...
```

或使用 `initdb` 脚本初始化：

```bash
# 准备 init.sql
echo "CREATE USER appuser WITH PASSWORD 'apppass';" > init.sql
# 挂载到 docker-entrypoint-initdb.d
docker run ... -v $(pwd)/init.sql:/docker-entrypoint-initdb.d/init.sql ...
```

> 官方镜像会在首次启动时执行 `/docker-entrypoint-initdb.d/` 下的 `.sql` 或 `.sh` 脚本。

#### 5.5 连接容器内数据库

```bash
# 进入容器执行 psql
docker exec -it mypg psql -U postgres
# 或从宿主机连接
psql -h localhost -U postgres -d postgres
```


---

### 六、安装后关键配置与安全加固

无论何种方式安装，以下配置至关重要。

#### 6.1 修改监听地址（允许远程访问）

编辑 `postgresql.conf` ：

```
listen_addresses = '*'   # 或指定 IP，如 'localhost,192.168.1.100'
port = 5432
```

> 仅在必要时开启，配合防火墙使用。

#### 6.2 配置客户端认证（pg_hba.conf）

典型配置（位于数据目录下）：

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
host    mydb            appuser         192.168.1.0/24          md5
```

* `md5` ：密码加密认证
* `trust` ：无密码（仅限本地测试）
* 修改后需重载配置： `SELECT pg_reload_conf();` 或 `systemctl reload postgresql`

#### 6.3 创建应用用户与数据库

```sql
-- 登录 psql
sudo -u postgres psql
-- 创建用户
CREATE USER myapp WITH PASSWORD 'strongpassword';
-- 创建数据库并授权
CREATE DATABASE myapp OWNER myapp;
-- 退出
\q
```

#### 6.4 设置环境变量（可选）

为方便命令行使用，可将 `psql` 加入 PATH：

* Linux/macOS: `export PATH="/usr/pgsql-16/bin:$PATH"` （加入 `~/.bashrc` ）
* Windows: 系统环境变量 → Path → 添加 `C:\Program Files\PostgreSQL\16\bin`


---

### 七、常见问题排查

#### 7.1 "psql: command not found"

* 原因：PATH 未包含 PostgreSQL bin 目录。
* 解决：按上述"环境变量"设置。

#### 7.2 "FATAL: password authentication failed"

* 检查 `pg_hba.conf` 是否为 `md5` ；
* 确认密码正确；
* 重启或重载服务使配置生效。

#### 7.3 端口被占用

* 查找占用进程： `sudo lsof -i :5432` （Linux/macOS）或 `netstat -ano | findstr :5432` （Windows）
* 终止进程或修改 PostgreSQL 端口。

#### 7.4 中文乱码

* 确保数据库创建时指定 `LC_COLLATE='zh_CN.UTF-8'` （Linux）；
* 客户端终端编码为 UTF-8；
* 在 `postgresql.conf` 中设置 `client_encoding = 'UTF8'` 。

最后总结：

| 平台 | 推荐方式 | 适用场景 |
|----|----|----|
| Ubuntu | 官方 APT 仓库 | 生产服务器、云主机 |
| CentOS | 官方 YUM 仓库 | 企业级 Linux 服务器 |
| Windows | EDB 图形安装程序 | 桌面开发、学习 |
| macOS | Homebrew 或 Postgres.app | 本地开发、快速原型 |
| 任意平台 | Docker 容器 | 微服务、CI/CD、隔离测试 |

> **核心原则** ：
>
> * **生产环境** ：优先使用系统包管理器（APT/YUM），便于维护和监控；
> * **开发环境** ：Docker 或 Postgres.app 提供最大灵活性；
> * **安全第一** ：始终设置强密码、限制远程访问、定期更新。

PostgreSQL 的安装只是第一步，后续还需关注备份策略（ `pg_dump` / `pg_basebackup` ）、性能调优（ `shared_buffers`, `work_mem` ）、高可用（流复制、Patroni）等进阶主题。

> 提醒：安装完成后，立即运行 `\conninfo` 和 `SELECT version();` 验证环境，并尝试创建第一个数据库。

\---

## 相关笔记

- [[homelab/数据库/CloudBeaver 部署与恢复手册.md]] — Web 端管理这个 PostgreSQL 实例