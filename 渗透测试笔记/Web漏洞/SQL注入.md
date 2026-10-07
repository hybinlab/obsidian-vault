---
publish: true
tags:
  - 渗透测试
  - Web漏洞
---
## 💻 SQL 注入漏洞 

### 🎯 概述

* **背景**：Web 应用程序通过 **SQL 查询**与数据库进行交互，以结构化地存储、修改和检索数据。
* **SQL 注入**：当用户输入未被**正确消毒 (sanitized)**（即未经验证）时，攻击者可以操纵输入，写入将在数据库中执行的 SQL 查询，从而执行攻击者所需的操作。
* **危害**：SQL 注入具有非常有害的影响，因为成功的攻击可能**危及组织存储在数据库中的关键数据**。

### 📝 正常登录时的 SQL 查询（无漏洞）

假设一个登录页面要求输入用户名和密码：

| 字段 | 输入数据 |
|:---|:---|
| **Username** | John |
| **Password** | Un@detectable444 |

Web 应用程序将构建并发送以下 SQL 查询到数据库：

```sql
SELECT * FROM users WHERE username = 'John' AND password = 'Un@detectable444';
```

* **逻辑**：数据库将检查是否存在用户名和密码**同时匹配**的用户（由布尔运算符 `AND` 分隔）。
* **结果**：如果找到匹配项，则返回用户的详细信息，允许登录。

### 💥 SQL 注入攻击示例（绕过登录）

假设该登录页面**缺乏输入验证和消毒**，即它容易受到 SQL 注入的攻击。

攻击者不知道用户 John 的密码，输入以下内容：

| 字段 | 注入输入 |
|:---|:---|
| **Username** | John |
| **Password** | `abc' OR 1=1;-- -` |

应用程序发送到数据库的 SQL 查询将变为：

```sql
SELECT * FROM users WHERE username = 'John' AND password = 'abc' OR 1=1;-- -';
```

#### **注入分析**


1. **初始检查**：查询首先检查是否有用户 `John`。
2. **第一个条件**：它检查 `username = 'John' AND password = 'abc'`。这几乎肯定会**失败**。
3. **注入逻辑**：查询在密码条件之后引入了一个 `**OR**` 运算符，并添加了语句 `**1=1**`。
   * `**OR**` 意味着只要**其中任何一个条件**为真，整个 SQL 查询就成功。
   * `**1=1**` 语句**永远为真**，这使得整个 `WHERE` 子句（对于用户 John）成功通过验证。
4. **注释符**：注入字符串末尾的 `**-- -**` 是 SQL 中的注释符（空格和 `-` 之间，MySQL/PostgreSQL 中为两个连字符加空格），它会注释掉查询中 `1=1` 之后的所有内容（在本例中，即原始查询末尾的**闭合单引号** `**'**`）。
5. **核心要点（单引号的作用）**：
   * 注入的单引号 `**'**` (在 `abc'` 之后) 用于**闭合**原始查询中用于封装密码字符串的单引号。
   * 通过闭合密码字符串，攻击者可以引入新的逻辑条件 `OR 1=1`。

<!-- end list -->

* **最终结果**：由于 `1=1` 为真，查询成功执行，攻击者被**以 John 的身份登录**。


## 🛠️ SQLMap

### 🎯 什么是 SQLMap

* **定义**：SQLMap 是一个**自动化工具**，用于检测和利用 Web 应用程序中的 **SQL 注入漏洞**。
* **用途**：它简化了发现和利用这些漏洞的过程。
* **环境**：它是一个**命令行工具**，通常内置于某些 Linux 发行版中，或者可以轻松安装。

### 🚀 SQLMap 的基本使用方法

#### 1. 启动和帮助

* **查看帮助**：使用 `--help` 标志可以列出所有可用的标志。
* **交互式向导**：对于初学者，可以使用 `--wizard` 标志。该工具会引导用户完成每一步，并通过提问来完成扫描。
  * **命令**：`sqlmap --wizard`

#### 2. 核心枚举标志 (Flags)

| 标志 | 目的 | 示例 |
|:---|:---|:---|
| `-u` | 指定**目标 URL**（用于 HTTP GET-based testing） | `sqlmap -u http://sqlmaptesting.thm/search/cat=1` |
| `--dbs` | **提取**所有**数据库名称** | `sqlmap -u [URL] --dbs` |
| `-D [db_name] --tables` | 结合数据库名 (`-D`)，**提取**该数据库中的所有**表名** | `sqlmap -u [URL] -D users --tables` |
| `-D [db_name] -T [table_name] --dump` | 结合数据库名 (`-D`) 和表名 (`-T`)，**导出**该表中的所有**记录/数据** | `sqlmap -u [URL] -D users -T thomas --dump` |

### 🔍 自动化 SQL 注入的步骤 (GET 参数测试)

这种方法适用于 URL 中使用 **GET 参数**来检索数据的 Web 应用程序（例如：`http://example.com/search?id=1`）。

#### 步骤 1: 扫描 URL 识别漏洞

* **目标**：测试带有 GET 参数的 URL 是否存在 SQL 注入漏洞。
* **命令示例**：`sqlmap -u http://sqlmaptesting.thm/search/cat=1`
* **结果分析**：SQLMap 会识别出 URL 中的 GET 参数 (`cat`) 是否是**动态的**，并报告发现的**注入类型**（例如：布尔盲注、基于错误、时间盲注、联合查询等） testing if GET parameter 'cat' is dynamic, \[INFO\] GET parameter 'cat' appears to be 'MySQL >= 5.0.12 AND time-based blind' injectable, Type: boolean-based blind, Type: error-based, Type: AND/OR time-based blind, Type: UNION query\]。

#### 步骤 2: 提取数据库名称

* **命令**：`sqlmap -u http://sqlmaptesting.thm/search/cat=1 --dbs`
* **结果**：显示可用的数据库名称，例如 `users` 和 `members`: \[*\] users \[*\] members\]。

#### 步骤 3: 提取特定数据库中的表名

* **目标**：以 `users` 数据库为例，提取其中的所有表名。
* **命令**：`sqlmap -u http://sqlmaptesting.thm/search/cat=1 -D users --tables`
* **结果**：显示该数据库中的表，例如 `johnath`、`alexas`、`thomas` +-----------+ | johnath | | alexas | | thomas | +-----------+\]。

#### 步骤 4: 导出特定表中的记录

* **目标**：导出 `thomas` 表中的所有记录。
* **命令**：`sqlmap -u http://sqlmaptesting.thmsearch/cat=1 -D users -T thomas --dump`
* **结果**：显示表中的数据，例如 `Date`、`name`、`pass` 字段及其值 +---------------------+------------+---------+ | Date | name | pass | +---------------------+------------+---------- | 09/09/2024 | Thomas THM | testing | +---------------------+------------+---------+\]。

### 📩 POST 参数测试

* **适用场景**：适用于应用程序通过**请求体 (request's body)** 而非 URL 发送数据的情况，例如登录或注册表单。
* **操作**：需要**拦截 (intercept)** 登录或注册页面上的 POST 请求，并将其保存为文本文件。
* **命令**：使用 `-r` 标志将保存的请求文件作为输入传递给 SQLMap。
  * **示例**：`sqlmap -r intercepted_request.txt`