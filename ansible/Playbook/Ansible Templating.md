---
publish: true
---
## Templating（Jinja2）

Ansible 用 **Jinja2** 模板引擎实现动态表达式，访问变量和 Facts。这是 [[ansible/Playbook/Ansible Playbook 进阶主题索引.md]] 中的第一个进阶主题。

## 核心概念

- **解析发生在控制节点**，不是目标机器 —— 意味着受管节点不需要装 Jinja2，减少依赖要求
- 用双花括号 `{{ }}` 引用变量、Facts、执行表达式
- 不仅能用在 `template` 模块的模板文件里，Playbook 里几乎任何字符串字段都能用

## 基本语法

```jinja2
My name is {{ ansible_facts['hostname'] }}
```

```yaml
# playbook 中直接引用变量
- name: 打印主机名
  ansible.builtin.debug:
    msg: "当前主机是 {{ ansible_facts['hostname'] }}"

# 甚至 task 的 name 本身也能模板化
- name: "配置 {{ inventory_hostname }} 的 nginx"
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
```

## 在 template 模块中使用

```
project/
├── site.yml
└── templates/
    └── nginx.conf.j2
```

```yaml
# site.yml
- name: 渲染 nginx 配置模板
  ansible.builtin.template:
    src: templates/nginx.conf.j2
    dest: /etc/nginx/nginx.conf
```

```jinja2
{# templates/nginx.conf.j2 #}
server {
    listen {{ http_port }};
    server_name {{ ansible_facts['hostname'] }};
}
```

> 模板文件必须是 **UTF-8 编码**。

## YAML 中的常见坑：什么时候要加引号

YAML 解析器看到 `{{ }}` 开头的行会误判为字典字面量，必须加引号：

```yaml
# 错误：以 { 开头，YAML 会尝试解析成字典，报错
- name: 设置端口
  vars:
    port: {{ http_port }}

# 正确：加引号
- name: 设置端口
  vars:
    port: "{{ http_port }}"
```

规则：**只要 `{{ }}` 是这一行值的开头，就要加引号**；如果是拼在字符串中间，可以不加：

```yaml
msg: "端口号是 {{ http_port }}"   # 拼接在字符串中，不强制要求引号，但加上更安全
msg: "{{ http_port }}"            # 整行就是变量，必须加引号
port: "{{ http_port }}"           # 同上，必须加引号
```

## 常用 Jinja2 语法

### 条件表达式（三元运算）

```jinja2
{{ "生产环境" if env == "prod" else "测试环境" }}
```

```yaml
- name: 根据环境设置副本数
  set_fact:
    replicas: "{{ 5 if env == 'prod' else 1 }}"
```

### 过滤器（filter）

用 `|` 管道对变量做转换：

```jinja2
{{ my_list | length }}              {# 列表长度 #}
{{ my_var | default('N/A') }}       {# 变量未定义时用默认值 #}
{{ my_string | upper }}             {# 转大写 #}
{{ my_list | join(',') }}           {# 列表转字符串 #}
{{ my_dict | to_json }}             {# 转 JSON #}
```

详见进阶主题索引中的 **Filters** 部分（[[ansible/Playbook/Ansible Playbook 进阶主题索引.md]]）。

### 循环和条件（模板文件内）

模板文件（`.j2`）里可以用 `{% %}` 写控制流：

```jinja2
{# templates/hosts.j2 #}
{% for host in groups['webservers'] %}
{{ hostvars[host]['ansible_host'] }}  {{ host }}
{% endfor %}

{% if env == "prod" %}
# 生产环境专属配置
worker_processes auto;
{% else %}
worker_processes 1;
{% endif %}
```

### 访问 Facts 和 hostvars

```jinja2
{{ ansible_facts['default_ipv4']['address'] }}
{{ ansible_facts['os_family'] }}
{{ hostvars['web1']['ansible_host'] }}
```

## 变量赋值：set_fact 配合模板

```yaml
- name: 计算派生变量
  set_fact:
    full_domain: "{{ hostname }}.{{ domain }}"

- name: 使用派生变量
  debug:
    msg: "完整域名: {{ full_domain }}"
```

## 安全注意事项

- **不要把用户输入直接拼进 `command`/`shell` 模块的模板字符串**，可能有注入风险；优先用模块参数而非拼接命令
- Jinja2 模板中避免暴露敏感变量到日志（可用 `no_log: true` 抑制输出）

```yaml
- name: 处理密码（避免日志泄露）
  ansible.builtin.debug:
    msg: "密码是 {{ db_password }}"
  no_log: true
```

## 实战例子：生成配置文件

```yaml
---
- hosts: webservers
  vars:
    http_port: 8080
    max_clients: 200
  tasks:
    - name: 渲染 nginx 配置
      ansible.builtin.template:
        src: templates/nginx.conf.j2
        dest: /etc/nginx/nginx.conf
      notify: restart nginx

  handlers:
    - name: restart nginx
      ansible.builtin.service:
        name: nginx
        state: restarted
```

```jinja2
{# templates/nginx.conf.j2 #}
server {
    listen {{ http_port }};
    server_name {{ ansible_facts['hostname'] }};

    location / {
        limit_conn addr {{ max_clients }};
        {% if env is defined and env == 'prod' %}
        access_log /var/log/nginx/access.log;
        {% else %}
        access_log off;
        {% endif %}
    }
}
```

## 提示

- 需要"纯渲染文本文件"用 `template` 模块；只是"传变量给模块参数"直接在 YAML 里写 `{{ }}` 即可，不需要单独的模板文件
- Jinja2 报错时，先检查是不是漏了引号，或者变量名拼错、变量未定义（用 `| default(...)` 兜底）
- 复杂逻辑（多层 if/for）建议放到模板文件（`.j2`）里，而不是塞进一行 YAML，可读性更好

## 相关笔记

- [[ansible/Playbook/Ansible Playbook 进阶主题索引.md]] — 其他进阶主题一览（Filters、Tests、Loops 等）
- [[ansible/Playbook/Ansible Playbook 编写.md]] — Playbook 基础语法
- [[ansible/Ansible 模块.md]] — template 模块的基本用法
