---
tags:
  - linux
  - 命令
publish: true
---
## 基本语法

```bash
grep [选项] 模式 文件
```

---

## 常用参数

|参数|说明|
|---|---|
|`-i`|忽略大小写|
|`-n`|显示行号|
|`-v`|反向匹配（不包含该模式的行）|
|`-r`|递归搜索目录|
|`-l`|只显示匹配的文件名，不显示内容|
|`-c`|只显示匹配的行数|
|`-E`|使用扩展正则表达式（ERE）|
|`-F`|把模式当作固定字符串，不解析正则|
|`-w`|精确匹配整个单词|
|`-x`|精确匹配整行|
|`-A n`|显示匹配行及后n行|
|`-B n`|显示匹配行及前n行|
|`-C n`|显示匹配行及前后各n行|
|`--color`|高亮显示匹配内容|

---

## 基本用法

```bash
# 搜索文件
grep "error" /var/log/syslog

# 忽略大小写
grep -i "error" file.log

# 显示行号
grep -n "error" file.log

# 反向匹配
grep -v "DEBUG" file.log

# 递归搜索目录
grep -r "password" /etc/

# 只显示文件名
grep -rl "error" /var/log/

# 统计匹配行数
grep -c "error" file.log

# 精确匹配单词（不匹配errors、error_log等）
grep -w "error" file.log
```

---

## 正则表达式

```bash
# 扩展正则，支持 | + ? {}
grep -E "error|warn|critical" file.log

# 匹配以error开头的行
grep "^error" file.log

# 匹配以.log结尾的行
grep "\.log$" file.log

# 匹配IP地址（简单版）
grep -E "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" access.log

# 匹配空行
grep "^$" file.txt

# 匹配非空行
grep -v "^$" file.txt
```

---

## 上下文显示

```bash
# 显示匹配行及后3行
grep -A 3 "error" file.log

# 显示匹配行及前3行
grep -B 3 "error" file.log

# 显示匹配行及前后各3行（排查问题时最常用）
grep -C 3 "error" file.log
```

---

## 高频组合

### 日志排查

```bash
# 实时跟踪日志中的错误
tail -f app.log | grep -i "error"

# 过滤多个关键词
tail -f app.log | grep -E "error|warn|exception"

# 排查某时间段的错误（日志带时间戳）
grep "2026-08-12" app.log | grep -i "error"

# 查看错误前后的上下文
grep -C 5 "OutOfMemory" app.log
```

### 进程管理

```bash
# 查找进程（过滤掉grep自身）
ps aux | grep nginx | grep -v grep

# 查找占用特定端口的进程
ss -tunlp | grep 8080
```

### 文件搜索

```bash
# 在项目中搜索某个函数定义
grep -rn "def main" /project/

# 搜索配置文件中的某项
grep -r "listen 80" /etc/nginx/

# 找出包含密码的配置文件（安全审计）
grep -rl "password" /etc/

# 搜索并忽略特定目录
grep -r "TODO" /project/ --exclude-dir=".git"
```

### 数据处理

```bash
# 统计日志中各种错误的数量
grep -c "error" app.log
grep -c "warn" app.log

# 提取所有IP地址
grep -oE "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" access.log

# 配合sort/uniq统计最多的IP
grep -oE "[0-9]{1,3}(\.[0-9]{1,3}){3}" access.log | sort | uniq -c | sort -rn | head -10

# 过滤空行和注释行
grep -v "^#" config.conf | grep -v "^$"
```

### 配合xargs批量操作

```bash
# 找出包含error的文件并查看
grep -rl "error" /var/log/ | xargs ls -lh

# 批量替换（配合sed）
grep -rl "old_string" /project/ | xargs sed -i 's/old_string/new_string/g'
```

---

## grep vs ag vs ripgrep

|工具|特点|
|---|---|
|`grep`|系统自带，兼容性最好|
|`ag`（the_silver_searcher）|比grep快，自动忽略.gitignore|
|`rg`（ripgrep）|最快，自动忽略.gitignore，推荐开发场景使用|

日常运维用`grep`就够，代码库搜索推荐`rg`。