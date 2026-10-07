### Docker 命令速查手册

> 目标：提供一份便于查阅的 Docker 命令手册，优先实用性与可复制性，覆盖镜像、容器、网络、数据卷、构建、Compose、日志排障、资源限制、安全与常见配方。

——

## 1. 快速上手与常用别名

* 安装验证：

```bash
docker version
docker info
```

* 常用别名（可加入 `~/.bashrc` 或 PowerShell Profile）：

```bash
alias d='docker'
alias dps='docker ps'
alias dpa='docker ps -a'
alias di='docker images'
alias dnc='docker network'
alias dv='docker volume'
alias drm='docker rm'
alias drmi='docker rmi'
alias dxc='docker exec -it'
```

——

## 2. 镜像管理（Images）

* 搜索/拉取/查看：

```bash
docker search nginx
docker pull nginx:latest
docker images                      # 本地镜像列表
docker image ls --digests          # 显示 digest
```

* 详情/清理：

```bash
docker image inspect nginx:latest
docker rmi nginx:latest            # 删除镜像
docker image prune -a              # 清理未使用镜像
```

* 导出/导入/保存：

```bash
docker save nginx:latest -o nginx.tar       # 保存为 tar（含层）
docker load -i nginx.tar                    # 从 tar 加载
docker image save busybox alpine | gzip > imgs.tgz
```

* 重新打标签与推送：

```bash
docker tag nginx:latest registry.example.com/prod/nginx:1.25
docker push registry.example.com/prod/nginx:1.25
```

* 构建（本地简单构建）：

```bash
docker build -t myapp:dev .
docker build -f Dockerfile.prod -t myapp:prod .
```

——

## 3. 容器管理（Containers）

* 运行与常用参数：

```bash
docker run --name web -d -p 8080:80 nginx:latest
docker run --rm -it alpine:latest sh                       # 退出即删除
docker run -d --restart=always --name redis redis:7        # 守护与重启策略
docker run -d --name app -e NODE_ENV=production myapp:dev  # 环境变量
docker run -d -v /host/data:/data -w /app myapp:dev        # 卷挂载与工作目录
docker run -d --cpus=1.5 --memory=512m myapp:dev           # 资源限制
```

* 查询与进入容器：

```bash
docker ps
docker ps -a
docker inspect web
docker logs -f --tail 200 web
docker exec -it web bash          # 或 sh
```

* 启停与删除：

```bash
docker stop web
docker start web
docker restart web
docker rm web                     # 停止后删除
docker rm -f web                  # 强制删除
docker container prune            # 清理已退出容器
```

* 复制文件：

```bash
docker cp web:/etc/nginx/nginx.conf ./nginx.conf
docker cp ./config.json web:/app/config.json
```

* 导出/导入容器文件系统（不含历史层）：

```bash
docker export web -o web.tar
cat web.tar | docker import - web:fs
```

——

## 4. 网络（Networks）

* 查看与创建：

```bash
docker network ls
docker network inspect bridge
docker network create --driver bridge app-net
```

* 连接/断开容器：

```bash
docker network connect app-net web
docker network disconnect app-net web
```

* 自定义子网/网关/内置 DNS：

```bash
docker network create \
  --driver bridge \
  --subnet 172.20.0.0/16 \
  --gateway 172.20.0.1 \
  app-net2
```

* 跨容器服务发现：同一自定义网络内可直接用容器名互相访问，例如 `curl http://web:80`。

——

## 5. 数据卷（Volumes）与绑定挂载（Bind Mount）

* 卷的管理：

```bash
docker volume ls
docker volume create app-data
docker volume inspect app-data
docker volume rm app-data
docker volume prune
```

* 容器挂载方式：

```bash
# 匿名卷
docker run -d -v /data redis:7

# 命名卷
docker run -d -v app-data:/var/lib/mysql mysql:8

# 绑定挂载（映射宿主路径）
docker run -d -v C:\\data:/data busybox
docker run -d -v /home/user/app:/app node:20
```

* 只读挂载、安全挂载：

```bash
docker run -d -v app-data:/data:ro nginx
docker run -d --mount type=bind,src=/logs,dst=/var/log,readonly alpine
```

——

## 6. 日志与排障（Logs & Debug）

* 查看日志：

```bash
docker logs web
docker logs -f --since 1h web
docker logs --tail 300 web
```

* 实时进入调试：

```bash
docker exec -it web bash
docker top web
docker stats                    # 资源监控
```

* 事件与系统清理：

```bash
docker events --since 10m
docker system df
docker system prune -a --volumes
```

* 健康检查结果：

```bash
docker inspect --format='{{json .State.Health}}' web | jq
```

——

## 7. 构建与 Dockerfile 速查

* 快速构建命令：

```bash
docker build -t repo/app:1.0 .
docker build --no-cache -t repo/app:clean .
docker build --build-arg NODE_ENV=production -t app:prod .
```

* 多阶段构建示例：

```Dockerfile
FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK CMD wget -qO- http://localhost/ || exit 1
```

* 常见指令速览：

```text
FROM  指定基础镜像
RUN   构建期执行命令
COPY  复制文件
ADD   高级复制（含解压、URL），优先用 COPY
ENV   设置环境变量
ARG   构建参数（仅构建期可见）
EXPOSE 暴露端口（文档性质）
WORKDIR 工作目录
ENTRYPOINT 启动入口
CMD   默认参数（可被 docker run 追加部分覆盖）
```

* 常见最佳实践：

```text
1) 选择精简镜像（alpine/distroless）
2) 合并 RUN 减少层数，并清理包缓存
3) 使用 .dockerignore 排除无关文件
4) 固定版本与校验包完整性
5) 将构建产物与运行时分离（多阶段）
```

——

## 8. 资源限制与运行安全

* 资源限制：

```bash
docker run -d \
  --cpus=2 \
  --memory=1g \
  --memory-swap=1g \
  --pids-limit=256 \
  myapp:prod
```

* 安全与权限：

```bash
docker run -d --read-only --cap-drop ALL --cap-add NET_BIND_SERVICE myapp
docker run -d --user 1000:1000 myapp
docker run -d --security-opt no-new-privileges myapp
```

* 只读根文件系统 + 可写挂载：

```bash
docker run -d --read-only -v app-tmp:/tmp -v app-logs:/var/log myapp
```

——

## 9. 网络暴露与端口映射

```bash
docker run -d -p 8080:80 nginx               # 宿主 8080 -> 容器 80
docker run -d -p 127.0.0.1:8080:80 nginx     # 仅本机访问
docker run -d -p 8080:80/tcp -p 9090:9090/udp image
```

——

## 10. Docker Compose（v2）

* 基本命令：

```bash
docker compose version
docker compose up -d                 # 启动/创建
docker compose down                  # 停止并删除
docker compose ps
docker compose logs -f web
docker compose restart web
```

* 示例 `compose.yaml`：

```yaml
services:
  web:
    image: nginx:1.25
    ports:
      - "8080:80"
    volumes:
      - ./site:/usr/share/nginx/html:ro
    networks:
      - appnet
  redis:
    image: redis:7
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis-data:/data
    networks:
      - appnet

volumes:
  redis-data:

networks:
  appnet:
    driver: bridge
```

* 常用选项：

```text
profiles: 条件启用服务
depends_on: 控制启动顺序（不等同健康依赖）
deploy: 生产编排建议使用 K8s/Swarm；Compose 更适合开发/小规模部署
```

——

## 11. Buildx 与多平台镜像

```bash
docker buildx create --use --name mybuilder
docker buildx inspect --bootstrap
docker buildx build --platform linux/amd64,linux/arm64 -t repo/app:multi --push .
```

——

## 12. 私有仓库与认证

* 登录与登出：

```bash
docker login registry.example.com
docker logout registry.example.com
```

* 推送与拉取：

```bash
docker tag app:1.0 registry.example.com/team/app:1.0
docker push registry.example.com/team/app:1.0
docker pull registry.example.com/team/app:1.0
```

* 不安全仓库（开发环境）：在 `daemon.json` 中配置 `insecure-registries`，生产不建议。

——

## 13. 导入导出、备份与迁移

* 镜像备份：`docker save` / `docker load`
* 容器文件系统：`docker export` / `docker import`
* 数据卷备份（通过临时容器）：

```bash
docker run --rm \
  -v app-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/app-data.tgz -C /data .
```

——

## 14. 常见系统文件与配置

* Linux：`/etc/docker/daemon.json`
* Windows：`C:\\ProgramData\\docker\\config\\daemon.json`

示例：

```json
{
  "registry-mirrors": ["https://mirror.example.com"],
  "insecure-registries": ["registry.local:5000"],
  "data-root": "/var/lib/docker"
}
```

——

## 15. 常见问题与排障建议

* 端口占用：

```bash
docker ps --filter publish=8080
# 或使用宿主工具 lsof/netstat 查占用
```

* 权限不足：为宿主目录设置合适权限，或使用 `--user` 指定非 root 账号。
* DNS 解析问题：自定义网络 + 内置 DNS，或在 `daemon.json` 配置 `dns`。
* 镜像过大：使用多阶段构建、alpine/distroless、清理缓存。
* 容器意外退出：查看 `docker logs`，`docker inspect` 中的 `State.ExitCode` 与 `Health`。

——

## 16. 高频实战配方（Recipes）

* 临时 BusyBox 工具箱：

```bash
docker run --rm -it --network host busybox:latest sh
```

* Nginx 反向代理本地服务：

```bash
docker run -d --name rproxy -p 80:80 \
  -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro nginx:1.25
```

* MySQL/Redis/PostgreSQL 开箱：

```bash
docker run -d --name mysql -e MYSQL_ROOT_PASSWORD=pass -p 3306:3306 mysql:8
docker run -d --name redis -p 6379:6379 redis:7
docker run -d --name pg -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres:15
```

* Node.js 开发挂载热更：

```bash
docker run --rm -it -p 5173:5173 -v $PWD:/app -w /app node:20 bash
```

* 以非 root 运行并映射端口 <1024：

```bash
docker run -d --user 1000:1000 --cap-add NET_BIND_SERVICE -p 80:80 myapp
```

——

## 17. 命令参考速查表

```text
镜像：pull | build | images | inspect | tag | push | rmi | save | load | prune
容器：run | ps | logs | exec | cp | stop | start | restart | rm | prune | inspect | stats | top
网络：network ls | inspect | create | connect | disconnect | prune
卷：volume ls | create | inspect | rm | prune
系统：system df | prune | events | info | version
Compose：compose up | down | ps | logs | restart | exec | cp | run | build
```

——

## 18. 参考与最佳实践要点

* 固定镜像版本与校验来源；生产关闭 `latest`。
* 组合健康检查 + 重启策略提升服务韧性。
* 通过网络隔离、只读根文件系统、最小权限运行强化安全。
* 定期 `prune` 与镜像体积治理，控制磁盘使用。
* 区分开发与生产配置：开发偏 Compose，生产趋向 K8s/编排平台。

——

本文档为速查手册，建议结合团队约束与环境规范进行二次封装（模板、脚本与 Compose 片段库）。