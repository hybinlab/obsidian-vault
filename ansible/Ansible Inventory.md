---
publish: true
---
## 配置文件位置

默认：`/etc/ansible/hosts`

Ansible 主配置文件存在**优先级顺序**（表16-2），如果当前目录或用户家目录中也有配置文件，则以自己新建的为准。

|优先级|文件位置|
|---|---|
|1（最高）|`ANSIBLE_CONFIG` 环境变量指定的路径|
|2|`./ansible.cfg`（当前目录）|
|3|`~/.ansible.cfg`（用户家目录）|
|4（最低）|`/etc/ansible/ansible.cfg`（系统默认）|

## 主机清单示例

```ini
# /etc/ansible/hosts
[dev]
192.168.10.20

[test]
192.168.10.21

[prod]
192.168.10.22
192.168.10.23

[balancers]
192.168.10.24
```

## 查看主机清单结构

```bash
ansible-inventory --graph
```

输出示例：

```
@all:
  |--@balancers:
  |  |--192.168.10.24
  |--@dev:
  |  |--192.168.10.20
  |--@prod:
  |  |--192.168.10.22
  |  |--192.168.10.23
  |--@test:
  |  |--192.168.10.21
  |--@ungrouped:
```

修改后**立即生效**，无需重启服务。

## INI 格式 vs YAML 格式

两种格式功能等价，选谁看规模：

- **INI**：节点少时更直观、写起来简单（如上面的示例）
- **YAML**：节点变多时更合适，能给每个节点声明唯一名称，并显式指定 `ansible_host` 字段

YAML 写法示例（等价于上面的 INI 示例）：

```yaml
all:
  children:
    dev:
      hosts:
        dev1:
          ansible_host: 192.168.10.20
    test:
      hosts:
        test1:
          ansible_host: 192.168.10.21
    prod:
      hosts:
        prod1:
          ansible_host: 192.168.10.22
        prod2:
          ansible_host: 192.168.10.23
    balancers:
      hosts:
        lb1:
          ansible_host: 192.168.10.24
```

## 建立 Inventory 的技巧

- **组名**要有意义且唯一（区分大小写），避免空格、连字符、数字开头（用 `floor_19` 而不是 `19th_floor`）
- 按三个维度分组，便于后续按需组合：
  - **What**（拓扑）：db、web、leaf、spine
  - **Where**（地理位置）：数据中心、区域、楼层
  - **When**（阶段）：dev、test、staging、prod
- 用 `children` 语法把多个组归到一个"父组"（元组），实现层级结构；一个组可以属于多个父组，但为了继承关系清晰可预测，建议每个组只挂一个父组
- **变量**可以设在主机级（单个节点）或组级（整组统一，如登录用户名），子组变量会覆盖父组变量
- 建好后用 `ansible-inventory --list`（或 `--graph`）验证结构是否符合预期，再用 `ansible all -m ping` 测试连通性
