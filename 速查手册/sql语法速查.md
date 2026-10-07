### 一些最重要的 SQL 命令

* **SELECT** - 从数据库中提取数据
* **UPDATE** - 更新数据库中的数据
* **DELETE** - 从数据库中删除数据
* **INSERT INTO** - 向数据库中插入新数据
* **CREATE DATABASE** - 创建新数据库
* **ALTER DATABASE** - 修改数据库
* **CREATE TABLE** - 创建新表
* **ALTER TABLE** - 变更（改变）数据库表
* **DROP TABLE** - 删除表
* **CREATE INDEX** - 创建索引（搜索键）
* **DROP INDEX** - 删除索引


## SELECT

```sql
SELECT column_name(s)
FROM table_name
WHERE condition
ORDER BY column_name [ASC|DESC]
```

* `column_name(s)`: 要查询的列。
* `table_name`: 要查询的表。
* `condition`: 查询条件（可选）。
* `ORDER BY`: 排序方式，`ASC` 表示升序，`DESC` 表示降序（可选）。


## INSERT INTO

```sql
INSERT INTO table_name (column1, column2, ...)
VALUES (value1, value2, ...)
```

* `table_name`: 要插入数据的表。
* `column1, column2, ...`: 要插入数据的列。
* `value1, value2, ...`: 对应列的值。


## UPDATE

```sql
UPDATE table_name
SET column1 = value1, column2 = value2, ...
WHERE condition
```

* `table_name`: 要更新数据的表。
* `column1 = value1, column2 = value2, ...`: 要更新的列及其新值。
* `condition`: 更新条件。


## DELETE

```sql
DELETE FROM table_name
WHERE condition
```

* `table_name`: 要删除数据的表。
* `condition`: 删除条件。


## CREATE TABLE

```sql
CREATE TABLE table_name (
    column1 data_type constraint,
    column2 data_type constraint,
    ...
)
```

* `table_name`: 要创建的表名。
* `column1, column2, ...`: 表的列。
* `data_type`: 列的数据类型（如 `INT`、`VARCHAR` 等）。
* `constraint`: 列的约束（如 `PRIMARY KEY`、`NOT NULL` 等）。


## ALTER TABLE(用于修改现有数据库表的结构。)

```sql
ALTER TABLE table_name
ADD column_name data_type
```

* `table_name`: 要修改的表。
* `column_name`: 要添加的列。
* `data_type`: 列的数据类型。

或:

```sql
ALTER TABLE table_name
DROP COLUMN column_name
```

* `column_name`: 要删除的列。


## DROP TABLE

```sql
DROP TABLE table_name
```

* `table_name`: 要删除的表。


## CREATE INDEX(用于创建索引)

```sql
CREATE INDEX index_name
ON table_name (column_name)
```

* `index_name`: 索引的名称。
* `column_name`: 要索引的列。


## DROP INDEX(删除索引)

```sql
DROP INDEX index_name
ON table_name
```


## WHERE

```sql
SELECT column_name(s)
FROM table_name
WHERE condition
```

* `condition`: 筛选条件。

下面的运算符可以在 WHERE 子句中使用：

| 运算符 | 描述 |
|----|----|
| = | 等于 |
| <> | 不等于。**注释：**在 SQL 的一些版本中，该操作符可被写成 != |
| > | 大于 |
| < | 小于 |
| >= | 大于等于 |
| <= | 小于等于 |
| BETWEEN | 在某个范围内 |
| LIKE | 搜索某种模式 |
| IN | 指定针对某个列的多个可能值 |


## ORDER BY(排序)

```sql
SELECT column_name(s)
FROM table_name
ORDER BY column_name [ASC|DESC]
```

* `column_name`: 用于排序的列。
* `ASC`: 升序（默认）。
* `DESC`: 降序。


## GROUP BY(将结果集按一列或多列进行分组)

```sql
SELECT column_name(s), aggregate_function(column_name)
FROM table_name
WHERE condition
GROUP BY column_name(s)
```

`aggregate_function`: 聚合函数（如 COUNT、SUM、AVG 等）


## HAVING(对分组后的结果集进行筛选)

```sql
SELECT column_name(s), aggregate_function(column_name)
FROM table_name
GROUP BY column_name(s)
HAVING condition
```

* `condition`: 筛选条件。


## JOIN(将两个或多个表的记录结合)

```sql
SELECT column_name(s)
FROM table_name1
JOIN table_name2
ON table_name1.column_name = table_name2.column_name
```

* `JOIN`: 可以是 INNER JOIN、LEFT JOIN、RIGHT JOIN 或 FULL JOIN。


## DISTINCT(返回唯一不同的值)

```sql
SELECT DISTINCT column_name(s)
FROM table_name
```

* `column_name(s)`: 要查询的列。


\
## SELECT TOP

```sql
SELECT column1, column2, ...
FROM table_name
LIMIT number;
```


## LIKE(模糊查询)

```sql
SELECT column1, column2, ...
FROM table_name
WHERE column_name LIKE pattern;
```

* **pattern**：搜索模式。

**通配符**

* `%`：匹配任意字符（包括零个字符）。
* `_`：匹配单个字符。

例子：


1. 使用 **%** 通配符找出所有以 "iPhone" 开头的产品：

```sql
SELECT ProductName, Category
FROM Products
WHERE ProductName LIKE 'iPhone%';
```


1. 使用 **_** 通配符找出所有产品名称第二个字符为 "e" 的产品：

```sql
SELECT ProductName, Category
FROM Products
WHERE ProductName LIKE '_e%';
```


## IN(在 WHERE 子句中规定多个值)

```sql
SELECT column1, column2, ...
FROM table_name
WHERE column IN (value1, value2, ...);
```

示例：(选取 name 为 "Google" 或 "菜鸟教程" 的所有网站：)

```sql
SELECT * FROM Websites
WHERE name IN ('Google','菜鸟教程');
```


## BETWEEN(选取介于两个值之间的数据范围内的值)

```sql
SELECT column1, column2, ...
FROM table_name
WHERE column BETWEEN value1 AND value2;
```

示例：


1. 选取 date 介于 '2016-05-10' 和 '2016-05-14' 之间的所有访问记录：

```sql
SELECT * FROM access_log
WHERE date BETWEEN '2016-05-10' AND '2016-05-14';
```

2\.选取 name 不介于 'A' 和 'H' 之间字母开始的所有网站：

```sql
SELECT * FROM WebsitesWHERE name NOT BETWEEN 'A' AND 'H';
```


## AS(为表名称或列名称指定别名)


1. 表的别名

```sql
SELECT column_name(s)
FROM table_name AS alias_name;
```


1. 列的别名

```sql
SELECT column_name AS alias_name
FROM table_name;
```


## JOIN(连接)

| 类型 | 描述 |
|----|----|
| **INNER JOIN** | 返回两个表中满足连接条件的记录（交集）。 |
| **LEFT JOIN** | 返回左表中的所有记录，即使右表中没有匹配的记录（保留左表）。 |
| **RIGHT JOIN** | 返回右表中的所有记录，即使左表中没有匹配的记录（保留右表）。 |
| **FULL OUTER JOIN** | 返回两个表的并集，包含匹配和不匹配的记录。 |
| **CROSS JOIN** | 返回两个表的笛卡尔积，每条左表记录与每条右表记录进行组合。 |
| **SELF JOIN** | 将一个表与自身连接。 |
| **NATURAL JOIN** | 基于同名字段自动匹配连接的表。 |


### INNER JOIN


:::info
INNER JOIN 与 JOIN 是相同的

:::

```sql
SELECT column_name(s)
FROM table1
INNER JOIN table2
ON table1.column_name=table2.column_name;
```

或:

```sql
SELECT column_name(s)
FROM table1
JOIN table2
ON table1.column_name=table2.column_name;
```


### UNION(合并结果集)

```sql
SELECT column1, column2, ...
FROM table1
UNION
SELECT column1, column2, ...
FROM table2;
```


:::info
UNION 操作符默认会去除重复的记录，如果需要保留所有重复记录，可以使用 UNION ALL 操作符。

:::

```sql
SELECT column1, column2, ...
FROM table1
UNION ALL
SELECT column1, column2, ...
FROM table2;
```


### CREATE

创建数据库

```sql
CREATE DATABASE dbname;
```


创建表

```sql
CREATE TABLE Persons
(
PersonID int,
LastName varchar(255),
FirstName varchar(255),
Address varchar(255),
City varchar(255)
);
```

## 

### 约束

SQL 中，我们有如下约束：

* **NOT NULL** - 指示某列不能存储 NULL 值。
* **UNIQUE** - 保证某列的每行必须有唯一的值。
* **PRIMARY KEY** - NOT NULL 和 UNIQUE 的结合。确保某列（或两个列多个列的结合）有唯一标识，有助于更容易更快速地找到表中的一个特定的记录。
* **FOREIGN KEY** - 保证一个表中的数据匹配另一个表中的值的参照完整性。
* **CHECK** - 保证列中的值符合指定的条件。
* **DEFAULT** - 规定没有给列赋值时的默认值。
* **INDEX** - 用于快速访问数据库表中的数据。


\