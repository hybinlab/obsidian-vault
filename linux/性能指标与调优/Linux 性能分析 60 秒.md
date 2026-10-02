---
publish: true
tags:
  - linux
  - 性能
---

整理自 Netflix 技术博客 *Linux Performance Analysis in 60,000 Milliseconds*。按自己的理解重写，示例都是自己机器（`docker-host`，10 个逻辑 CPU，Linux 6.8）上的输出。

**目的**：登上一台有性能问题的 Linux 机器后，用 10 条命令、约 60 秒，对 CPU、内存、磁盘、网络的状况有个大致印象。看懂这些指标，才能看懂 Prometheus 里 `node_exporter` 的指标（对应关系集中在文末）。

**约定**：标 ❓ 的是凭印象写、还没对照 `man` 或实测核对的内容。

## 方法：USE

对每一种资源（CPU、内存、磁盘、网络）检查三件事：

| 缩写 | 含义 | 例子 |
|---|---|---|
| **U**tilization | 利用率：资源有多忙 | CPU 使用 96% |
| **S**aturation | 饱和度：需求超过处理能力，有排队 | CPU 运行队列、磁盘请求队列 |
| **E**rrors | 错误数 | 丢包、重传、OOM |

先看**错误**和**饱和度**，因为它们容易理解。同时记录哪些资源已经排除，缩小后续排查范围。

## 十条命令

```bash
uptime
dmesg | tail
vmstat 1
mpstat -P ALL 1
pidstat 1
iostat -xzy 1
free -m
sar -n DEV 1
sar -n TCP,ETCP 1
top
```

`mpstat`、`pidstat`、`iostat`、`sar` 来自 `sysstat` 软件包，需要先安装。

**通用提醒：带间隔的采样命令，第一行 / 第一份报告是开机以来的平均值，忽略它。**（`vmstat`、`iostat` 都是这样；`iostat` 可以加 `-y` 直接省掉。）

### 1. uptime：负载均值

格式：`当前时间 up 运行时长, 登录会话数, load average: 1分钟, 5分钟, 15分钟`。

- 三个数是 1、5、15 分钟的负载均值（指数衰减的移动平均）。
- Linux 的负载 = **想在 CPU 上运行的进程** + **阻塞在不可中断 I/O（状态 `D`，多半是磁盘）的进程**。所以**负载不等于 CPU 使用率**。
- 是否过高，要**除以 CPU 核数**再看。
- **趋势比数值重要**：1 分钟值远低于 15 分钟值 → 问题可能已经过去；1 分钟值明显高于 15 分钟值 → 负载在上升，用 `vmstat`、`mpstat` 确认。
- 只能粗略看需求，定位要靠后面的命令。

**实例**

```
01:07:12 up 36 days,  5:43,  5 users,  load average: 1.78, 1.72, 1.35
```

- `5 users` 是登录**会话**数，不是不同用户的个数，开多个 SSH / VS Code Remote 窗口会偏多 ❓。
- `1.78 / 10 核 ≈ 0.18`，负载很低，平稳略升。这一步就足以排除「机器过载」。
- 约 1.0 来自那个吃满一个核的 ffmpeg（见[[#实战：一个核被吃满]]），其余是零星进程。`vmstat` 的 `b` 和 `iostat` 都显示没有磁盘等待，所以这里的负载基本来自 CPU。

### 2. dmesg | tail：内核消息

找可能导致性能问题的错误，**这一步不要漏**：

- `Out of memory` / `oom-killer`：OOM Killer 杀了进程，内存不足。
- `SYN flooding` / `Dropping request`：TCP 在丢弃连接请求。
- 磁盘或文件系统的 I/O 错误（我补的类别）。

时间戳是**开机以来的秒数**，要看墙上时间用 `dmesg -T`（休眠过的机器或虚拟机上可能不准 ❓）。

**Docker 主机上 `dmesg` 很吵**：每次容器启停都刷十来行 veth / 网桥日志，`tail` 的 10 行很容易被它们占满，真正的错误被挤出去。所以要过滤：

```bash
dmesg | grep -v -E "veth|br-|promiscuous|blocking|forwarding|disabled"
dmesg --level=err,warn          # 只看错误和警告 ❓
dmesg | grep -i -E "oom|out of memory|error|fail"
```

**实例**：`dmesg | tail` 的十行全是同一个容器的网络创建和销毁，**没有任何错误**。

```
[3131067.540791] vethafc7525: entered promiscuous mode
[3131067.566011] eth0: renamed from vethe3d9972
[3131067.578672] br-f79c54cb1d26: port 3(vethafc7525) entered forwarding state
[3131068.100640] br-f79c54cb1d26: port 3(vethafc7525) entered disabled state
[3131068.100704] vethe3d9972: renamed from eth0
[3131068.146214] vethafc7525 (unregistering): left promiscuous mode
...
```

- 读法：宿主机侧 veth 挂到网桥 → 另一端移进容器改名 `eth0` → 端口 `forwarding`（网络可用）→ 容器退出，`eth0` 改回原名 → veth 注销。
- `forwarding`（…067.58）到 `disabled`（…068.10）只有约 0.5 秒，是个**瞬间启停的容器**：`docker run --rm` 的一次性任务、定时任务，或启动即崩溃，光看这十行分不出来。
- 每隔几秒就出现一组、而且是同一个网络 → 更像崩溃重启循环，去看那个容器的日志；只偶尔出现 → 多半是定时任务，不用管。
- 查是谁 ❓：`docker ps -a`（看 Restarting / 频繁 Exited）、`docker events --since 10m`、`docker network inspect br-f79c54cb1d26`（网桥名里是网络 ID 的前 12 位）。
- `3131067 / 86400 ≈ 36.2` 天，与 `uptime` 的 36 天吻合。

### 3. vmstat 1：系统整体概览

每秒一行。

| 组 | 列 | 含义 | 怎么判断 |
|---|---|---|---|
| procs | `r` | 在 CPU 上运行和等待运行的进程数 | **大于核数 = CPU 饱和**。比负载更准，因为不含 I/O 等待 |
| | `b` | 不可中断睡眠（多为等磁盘）的进程数 | 持续非 0 要看磁盘 |
| memory（KB） | `swpd` | **已用** swap 总量 | 不为 0 不代表正在换页，看 `si`/`so` |
| | `free` | 空闲内存 | 小不等于紧张，Linux 会拿空闲内存做缓存，看 `free -m` 的 `available` |
| | `buff` / `cache` | 块设备缓冲 / 页缓存 | |
| swap | `si` / `so` | 每秒换入 / 换出 | **非 0 说明内存不足** |
| io | `bi` / `bo` | 每秒从块设备读入 / 写出的块数（1 块 = 1 KB ❓） | |
| system | `in` / `cs` | 每秒中断数 / 上下文切换数 | |
| cpu | `us` `sy` `id` `wa` `st` | 用户态（含 nice ❓）、内核态、空闲、等 I/O、被偷走 | 见下 |
| | `gu` | 运行虚拟 CPU 的时间，新版 procps 才有 ❓ | |

CPU 时间的解读：
- `us + sy` 高说明 CPU 忙；超过 90% 也不一定有问题，要结合 `r` 看有没有排队。
- `sy` 平均超过 20% 值得深究，可能是内核处理 I/O 效率有问题。
- `wa` 持续偏高指向磁盘瓶颈。它其实是「空闲」的一种：CPU 闲着，因为任务在等磁盘。**`wa` 高不等于磁盘慢**，要用 `iostat` 确认。
- `st` 是被同宿主机的其他虚拟机占用的时间，只在虚拟化环境有意义。

**实例**

```
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st gu
 2  0 1473160 307368 1105964 11066868    0    0  2579    90 4574    4  9  0 90  0  0  0   ← 开机平均，忽略
 1  0 1473160 303084 1105972 11069120    0    0  2244    96 4666 3806 10  1 89  0  0  0
 1  0 1473160 298304 1105984 11071372    0    0  2244   180 5262 4382 11  1 89  0  0  0
 ...（共 8 个采样）
 1  0 1473160 284908 1105992 11085288    0    0  2244     4 5278 4604 10  1 89  0  0  0
```

1. **CPU 没饱和**：`r` 1–2 对 10 核；`b` 全 0。`us` 10–11% ≈ 一个核，就是那个 ffmpeg（mpstat 里的 `%nice` 在这里并进了 `us` ❓）。`wa`、`st` 为 0。
2. **`swpd` ≈ 1.4 GB 但 `si`/`so` 全 0**：swap 里有很久以前换出去的不活跃页，当前没有换页，内存不紧张。
3. **`free` 只有 0.3 GB，`cache` 有 10.6 GB**：正常现象。
4. **`cache` 的增速 = 磁盘读入速度**：7 秒内 `cache` 涨了 16168 KB ≈ **2310 KB/s**，`bi` 平均 ≈ **2320 KB/s**，和 `iostat` 里 sdb 的 `rkB/s ≈ 2563` 也吻合。也就是 ffmpeg 读进来的视频文件全部留在了页缓存里。`free` 同期每秒降约 2597 KB，多出的约 290 KB/s 是其他内存分配。
5. `bo` 0–300、`in` 约 4600–6200/s、`cs` 约 3800–5900/s，在 10 核机器上都很低。

结论：CPU、内存、磁盘都没压力，唯一持续发生的事是 ffmpeg 读文件、占一个核。

### 4. mpstat -P ALL 1：每个 CPU 的使用情况

按单个 CPU 打印时间占比，用来发现**不均衡**：**只有一个核特别忙，往往是单线程应用**。各字段都是 CPU 时间的分类，加起来约 100%。

| 字段 | 含义 | 看什么 |
|---|---|---|
| `%usr` | 普通用户态 | 应用本身在算 |
| `%nice` | nice 值被调高（优先级降低）的用户态程序；负 nice 算进 `%usr` ❓ | 备份、压缩、批处理等 |
| `%sys` | 内核态 | 系统调用、I/O 处理，持续偏高值得深究 |
| `%iowait` | CPU 空闲，且有未完成的磁盘 I/O | 同 vmstat 的 `wa` |
| `%irq` / `%soft` | 硬中断 / 软中断 | 网络包多时 `%soft` 会升高 |
| `%steal` | 被 hypervisor 抢走的时间 | 只在虚拟机里有意义 |
| `%guest` / `%gnice` | 运行虚拟 CPU 的时间 / 其中 nice 过的部分 ❓ | 宿主机跑虚拟机时才有 |
| `%idle` | 空闲，且没有未完成的磁盘 I/O | |

**实例：平均值掩盖了单核热点**（只留关键列）

```
Average:  CPU   %usr  %nice  %sys  %iowait  %steal  %idle
Average:  all   0.59  10.10  0.37    0.01    0.00   88.81
Average:    0   0.68   0.00  0.41    0.00    0.00   98.01
Average:    8   0.00  99.82  0.14    0.00    0.05    0.00
Average:    9   0.82   0.05  0.27    0.00    0.00   98.86
```

- `all` 行：88.81% 空闲，看起来很闲，只是 `%nice` 10.10% 偏高。
- 分核看：CPU 8 被 nice 过的任务占满，其余核 98–99% 空闲。10 个核的 `%nice` 加起来 ≈ 100.65，平均 10.07，与 `all` 吻合。
- **结论：这是「一个核被占满」，不是「整机 10% 忙」**。`all` 的平均值会掩盖单核热点，所以要 `-P ALL`。怎么找到是谁，见[[#实战：一个核被吃满]]。

### 5. pidstat 1：按进程看 CPU

类似 `top` 的进程摘要，但**滚动输出、不清屏**，适合看趋势，也方便贴进排查记录。

| 列 | 含义 |
|---|---|
| `UID` / `PID` | 用户 ID / 进程号 |
| `%usr` / `%system` / `%guest` | 用户态 / 内核态 / 虚拟 CPU 占比 |
| `%wait` | 进程在运行队列里**等着跑**的时间占比，较新版本才有 ❓ |
| `%CPU` | 总占比，**是所有 CPU 之和，可以超过 100%**，100% ≈ 1 个核 |
| `CPU` | 最近运行在哪个核上（会迁移，不代表绑定） |
| `Command` | 线程名，不是完整命令行 |

实测验证：`%CPU = %usr + %system + %guest`（ffmpeg：100.98 + 0.98 + 0.00 = 101.96）。

常用选项 ❓：`-l` 完整命令行、`-t` 按线程、`-d` 磁盘 I/O、`-r` 内存、`-p <pid>` 只看某个进程。默认不显示 nice 值，要看用 `ps -o ni` 或 `top`。

**实例**

```
UID    PID      %usr    %system  %guest  %wait  %CPU    CPU  Command
0      1631162  100.98  0.98     0.00    0.00   101.96  7    ffmpeg
0      1648238  0.98    0.98     0.00    0.00   1.96    2    pidstat
10001  3111674  0.98    0.98     0.00    0.00   1.96    2    loki
```

- **1% 以下的数字没有意义**：几乎所有数字都是 0.98 的倍数。推测是按时钟节拍统计（100 Hz，每拍 10 ms），一个采样周期约 1.02 秒，一拍就是 `10 / 1020 ≈ 0.98%`。只说明那一秒恰好被记了一拍 ❓。
- `pidstat` 自己也在列表里（1.96%），观测工具本身有开销。

### 6. iostat -xzy 1：磁盘

`-x` 扩展指标，`-z` 跳过没活动的设备，`-y` 省略开机以来的第一份报告。LVM 机器加 `-N`，把 `dm-0` 显示成 LVM 名字。

**avg-cpu 行**：与 mpstat 的 `all` 行同义。按 `man iostat`，`%iowait` 和 `%idle` 是同一种「空闲」按有没有未完成 I/O 拆成的两半，这正是「`%iowait` 不等于磁盘慢」的依据。

**设备行**（新版列名，已对照 `man iostat`）。按读（r）、写（w）、丢弃（d）、刷盘（f）四类分组：

| 列 | 含义 |
|---|---|
| `r/s` `w/s` | 每秒完成的读 / 写请求数（**合并之后**，即真正发给设备的），也就是 IOPS |
| `rkB/s` `wkB/s` | 每秒读 / 写的数据量（KB） |
| `rrqm/s` `wrqm/s`、`%rrqm` `%wrqm` | 每秒**被合并掉**的读 / 写请求数，及其占比 |
| `r_await` `w_await` | 读 / 写请求的平均耗时（ms），含排队和服务时间 |
| `rareq-sz` `wareq-sz` | 读 / 写请求的平均大小（KB） |
| `d/s` `dkB/s` `drqm/s` `%drqm` `d_await` `dareq-sz` | 同上，针对 discard（即 SSD 的 TRIM） |
| `f/s` `f_await` | 每秒 flush 请求数及平均耗时。分区不统计 flush；同一时刻最多执行一个 flush，所以 `f_await` 可能是单次的两倍 |
| `aqu-sz` | 平均请求队列长度 |
| `%util` | 有 I/O 请求在处理的时间占比 |

和旧版的区别：`avgqu-sz` → `aqu-sz`；`avgrq-sz` → `areq-sz`（单位从扇区改成 KB）；`await` 拆成了 `r_`/`w_`/`d_await`；`svctm` 已从 man 中移除（原因可能是不可靠 ❓）。

**怎么判断**

| 看什么 | 判断 |
|---|---|
| `r/s` `w/s` `rkB/s` `wkB/s` | 描述负载，有时问题就是负载太大 |
| `r_await` `w_await` | 应用实际感受到的延迟，偏高说明设备饱和或有问题 |
| `aqu-sz` | 大于 1 可能饱和（并行设备能同时处理多个，不绝对） |
| `%util` | 串行设备超过 60% 通常开始变慢，接近 100% 饱和。**SSD、RAID、逻辑盘这类并行设备不适用**（man 原话），100% 只说明一直有 I/O，后端可能远没满，要结合 `aqu-sz` 和 `await` |

另外，磁盘慢**不一定影响应用**：预读和缓冲让应用不必直接承受延迟。

**实例**（只留关键列）

| Device | r/s | rkB/s | rareq-sz | w/s | wkB/s | wrqm/s | w_await | %util |
|---|---|---|---|---|---|---|---|---|
| sda | 0.96 | 14.75 | 15.37 | 4.47 | 90.05 | 7.61 | 1.32 | 0.16 |
| dm-0 | 1.09 | 14.63 | 13.43 | 12.05 | 89.99 | 0.00 | 3.18 | 0.72 |
| sdb | 12.43 | 2563.61 | 206.29 | 0.00 | 0.00 | 0.00 | 25.00 | 2.95 |

1. **磁盘很闲**：`%util` 最大 2.95%，`aqu-sz` 最大 0.04。
2. **`rkB/s ≈ r/s × rareq-sz`**：sdb 是 12.43 × 206.29 ≈ 2564。每次约 206 KB，请求大、次数少，是顺序大块读，与 ffmpeg 读视频一致（sdb 应该是媒体盘，用 `lsblk` 确认）。
3. **合并的例子**：`dm-0`（LVM 逻辑卷，在 sda 之上，用 `lsblk` 确认）发了 12.05 次写/秒，到 sda 上是 4.47 次 + 合并掉的 7.61 次 = 12.08，数据量也几乎相同（89.99 vs 90.05 KB/s）。
4. **请求数接近 0 时，平均值是噪声**：sdb 的 `w_await 25.00` 对应的 `w/s` 是 0.00；`d_await` 高达 120524，但 `d/s` ≈ 0。**先看 `r/s`、`w/s`，再看耗时。**`-z` 不会过滤掉「有过 I/O 但四舍五入后是 0」的行。

### 7. free -m：内存

- `buffers`：块设备 I/O 用的缓冲区缓存；`cached`：文件系统用的页缓存。确认它们不接近 0 就行（接近 0 会导致更多磁盘 I/O）。
- Linux 会把空闲内存拿来做缓存，需要时能迅速回收，所以**看 `available` 列，不看 `free` 列** ❓。
- ZFS on Linux 有自己的缓存（ARC），不会正确反映在 `free` 里，可能显得空闲很少，实际还能让出来。

> 待补：自己机器上的输出。

### 8. sar -n DEV 1：网卡吞吐

看每个接口的收发包数和数据量，既是负载度量，也用来判断有没有碰到带宽上限。

> `sar` 的 `kB/s` 是**千字节**，网卡带宽通常用**比特**：`12.99 kB/s × 8 ≈ 104 kbit/s`。

| 列 | 含义 |
|---|---|
| `rxpck/s` `txpck/s` | 每秒收 / 发的包数 |
| `rxkB/s` `txkB/s` | 每秒收 / 发的千字节数 |
| `rxcmp/s` `txcmp/s` | 压缩包数，用于 cslip 等串行线路，以太网上恒为 0，忽略 |
| `rxmcst/s` | 每秒收到的组播包数 |
| `%ifutil` | 接口利用率，分母是接口速率。半双工取收发之和，全双工取收发中**较大**的那个 |

（`txpck/s`、`rxkB/s`、`txkB/s` 没对照到 man ❓，其余已核对。）

接口太多时只看真实网卡：`sar -n DEV 1 | grep -E "IFACE|ens18"`。

**实例**（采样 2 秒后 `Ctrl-C`，取 `Average:` 块）

| IFACE | rxpck/s | txpck/s | rxkB/s | txkB/s |
|---|---|---|---|---|
| `ens18` | 5.00 | 8.50 | 0.45 | 12.99 |
| `lo` | 3.00 | 3.00 | 0.22 | 0.22 |
| 其余几十个 `br-*`、`veth*` | 多数为 0 | | 约 0.06–0.13 | |

1. **网络几乎空闲**：`ens18` 发送约 104 kbit/s，离带宽上限差几个数量级。`%ifutil` 全是 0.00 是四舍五入的结果（对 1 Gbit/s 只有 0.01%）；虚拟网卡也可能拿不到链路速率 ❓。
2. **`br-*`、`veth*` 是 Docker 的虚拟接口**：每个 compose 网络一个 `br-<id>`，每个容器一个 `veth`，`docker0` 是默认网桥（用 `ip -br link`、`docker network ls` 确认）。
3. **不要把所有接口加起来当总流量**：容器间流量会同时出现在 `veth` 和 `br` 上，重复计算。出入口流量只看真实网卡。
4. `ens18` 发多收少（约 1.5 kB/包），像是被 Prometheus 抓 `/metrics`，只是猜测。

### 9. sar -n TCP,ETCP 1：TCP 概况

| 列 | 含义 |
|---|---|
| `active/s` | 本机主动发起的连接数/秒（`connect()`），粗略视为出站 |
| `passive/s` | 对端发起的连接数/秒（`accept()`），粗略视为入站 |
| `retrans/s` | 每秒 TCP 重传数 |

- active、passive 可粗略衡量服务器负载。「主动 = 出站」不严格，例如 localhost 连 localhost。
- **重传是网络或服务器问题的信号**：网络不可靠（如公网），或服务器过载在丢包。

> 待补：自己机器上的输出。

### 10. top：收尾

`top` 包含前面查过的很多指标，最后跑一次，看有没有和前面差别很大的，有的话说明负载在波动。缺点是清屏、不易看趋势，间歇性问题的证据容易丢；`Ctrl-S` 暂停，`Ctrl-Q` 继续；按 `1` 展开每个核。

> 待补：自己机器上的输出。

## 实战：一个核被吃满

把上面各节的实例串起来，是同一件事：

**1. 发现**：`mpstat -P ALL` 显示 CPU 8 的 `%nice` 是 99.82%，`all` 行 `%nice` 10.10%（见第 4 节）。

**2. 找进程**

```bash
ps -eo pid,psr,ni,pcpu,comm,args --sort=-pcpu | head -20
```

```
PID      PSR  NI   %CPU  COMMAND
1595723  5    10   101   ffmpeg
```

- `NI=10`，低优先级，所以内核把它的 CPU 时间记到 `%nice`，不记到 `%usr`。
- `%CPU 101` ≈ 1 个核，`1/10 ≈ 10%`，与 `%nice 10.10` 吻合。
- `PSR=5` 而不是 8 并不矛盾：PSR 只是最近运行的核，调度器会迁移它。**不要靠「哪个核高」认进程，看进程自己的 `%CPU`**。
- **坑**：`ps` 的 `%CPU` 是进程**整个生命周期**的平均，长期运行的进程会被拉低。要看当前占用用 `pidstat 1` 或 `top`。

**3. 它在做什么**：`/usr/lib/jellyfin-ffmpeg/ffmpeg`，由 Jellyfin 启动，关键参数：

| 参数 | 含义 |
|---|---|
| `-threads 1` | 单线程 → 恰好占满一个核，不会铺满 10 个 |
| `-an -sn` | 不处理音频、字幕 |
| `-vf fps=0.1,...scale=...320...` | 每 10 秒视频抽一帧，缩放到宽 320 以内 |
| `-c:v mjpeg -f image2`，输出 `/tmp/jellyfin/.../%08d.jpg` | 编码成 JPEG 写文件 |

判断是在生成 **Trickplay**（进度条预览缩略图）。这是根据参数推断的，可在 Jellyfin 计划任务里核对。

**4. 前后对上的账**

- `uptime` 负载约 1.78，其中约 1.0 来自它。
- `vmstat` 的 `us` 约 10%；`bi` ≈ `cache` 增速 ≈ 2.3 MB/s。
- `iostat` 的 sdb 在做 2.5 MB/s 的顺序大块读。
- 后来 `pidstat` 里 PID 变成了 `1631162`：上一个视频处理完，Jellyfin 起了新的 ffmpeg 处理下一个。

**5. 要不要管**：nice 过的批处理任务吃满一个核，有其他任务时会让出 CPU，通常无碍。要管，只取决于在不在意这段时间的功耗和风扇，或者它该不该在这个时候跑。

## 对应到 Prometheus（个人整理，非原文）

指标名是凭印象写的 ❓，请在自己的 Prometheus 里搜索确认，不同 `node_exporter` 版本可能有差异。CPU 时间、磁盘字节、网络字节、swap 换页都是 **Counter**，要先 `rate()`，见 [[Prometheus 指标类型]]。

| 命令 / 指标 | `node_exporter` 里的对应 |
|---|---|
| uptime 负载 | `node_load1`、`node_load5`、`node_load15` |
| uptime 运行时长 | `time() - node_boot_time_seconds`（秒） |
| CPU 核数 | `count(node_cpu_seconds_total{mode="idle"})` |
| vmstat `r` / `b` | `node_procs_running` / `node_procs_blocked` |
| vmstat / mpstat 的 CPU 占比 | `node_cpu_seconds_total{mode="..."}`，见下一小节 |
| vmstat `cs` | `node_context_switches_total` |
| vmstat `swpd` | `node_memory_SwapTotal_bytes - node_memory_SwapFree_bytes` |
| vmstat `si` / `so` | `rate(node_vmstat_pswpin[5m])` / `rate(node_vmstat_pswpout[5m])` |
| free `available` | `node_memory_MemAvailable_bytes`（Gauge） |
| iostat `r/s` `w/s` | `rate(node_disk_reads_completed_total[5m])`、`rate(node_disk_writes_completed_total[5m])` |
| iostat `rkB/s` `wkB/s` | `rate(node_disk_read_bytes_total[5m])`、`rate(node_disk_written_bytes_total[5m])` |
| iostat `%util` | `rate(node_disk_io_time_seconds_total[5m])`（0~1，乘 100） |
| sar `rxkB/s` `txkB/s` | `rate(node_network_receive_bytes_total[5m])`、`rate(node_network_transmit_bytes_total[5m])`（字节/秒，乘 8 得比特） |
| sar `rxpck/s` `txpck/s` | `node_network_receive_packets_total`、`node_network_transmit_packets_total` |
| 网卡丢包、错误 | `node_network_receive_drop_total`、`node_network_receive_errs_total` 等 |
| sar `retrans/s` | `rate(node_netstat_Tcp_RetransSegs[5m])` |
| dmesg 里的 OOM | `node_vmstat_oom_kill` |
| pidstat（按进程） | **没有**。`node_exporter` 只有整机指标；容器级用 cAdvisor（`container_cpu_usage_seconds_total`），进程级用 process-exporter |

网络指标按 `device` 区分接口，用 `device!~"veth.*|br-.*|docker0|lo"` 过滤掉虚拟接口。

```promql
# CPU 使用率（0~1，不含 idle）
1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))

# 每核负载（>1 表示排队）
node_load1 / count by (instance) (node_cpu_seconds_total{mode="idle"})
```

### mpstat 字段 ↔ `node_cpu_seconds_total`

两个关键标签：`cpu`（核编号）和 `mode`（时间分类）。

| mpstat | `%usr` | `%nice` | `%sys` | `%iowait` | `%irq` | `%soft` | `%steal` | `%idle` |
|---|---|---|---|---|---|---|---|---|
| `mode=` | `user` | `nice` | `system` | `iowait` | `irq` | `softirq` | `steal` | `idle` |

单位是「CPU 秒」，`rate()` 后是**每个核一个序列、取值 0~1 的占比**。要得到 mpstat 那样的数需要聚合：

```promql
# mpstat 的 all 行：整机各模式占比（%）
avg by (instance, mode) (rate(node_cpu_seconds_total[5m])) * 100

# mpstat -P ALL 的某个核
rate(node_cpu_seconds_total{cpu="8"}[5m]) * 100

# nice 占比最高的核（定位热点）
topk(3, rate(node_cpu_seconds_total{mode="nice"}[5m])) * 100
```

拿上面的实战验证：`avg(rate(node_cpu_seconds_total{mode="nice"}[5m]))` 应接近 `0.10`（= mpstat 的 10%）；换成 `sum` 会得到 `1.0`（= 消耗了 1 个核）。两个都对，只是单位不同。多台机器时加 `by (instance)`。

**学习方法**：看到一个 `node_exporter` 指标，就去 Linux 上找它对应的命令和原始概念，不要背指标名。`mode="nice"` 就是 mpstat 的 `%nice`，也就是内核 CPU 记账里的 nice 类别。

