---
publish: true
---

承接 [[监控告警链路追踪/Alloy/Alloy 配置语法入门.md]] 里 Expression 一节提到的"字面值"，这里展开 Alloy 语法支持的具体类型。

## 基础类型

| 类型 | 说明 | 例子 |
| --- | --- | --- |
| `number` | 数值，整数/无符号整数/浮点数统一处理，不区分 int 和 float | `3`、`3.14` |
| `string` | 双引号包裹的 Unicode 字符序列 | `"Hello, world!"` |
| `bool` | 布尔值 | `true`、`false` |
| `array` | 方括号包裹、逗号分隔的值序列 | `[1, 2, 3]` |
| `object` | 花括号包裹的键值对 | `{ name = "John" }` |
| `function` | 一段可执行例程，函数调用本身也是一个值 | `sys.env("HOME")` |
| `null` | 表示无值 | — |

数值不区分整数/浮点数，比较时按值相等，支持科学计数法：

```alloy
3    == 3.00     // true
5.0  == (10 / 2) // true
1e+2 == 100      // true
2e-3 == 0.002    // true
```

## 泛型类型标注（文档/类型签名里用）

- `any`：任意类型
- `map(T)`：所有值都是类型 T 的 object（比如 `map(string)` 就是值全是字符串的对象）
- `list(T)`：所有值都是类型 T 的 array
- `duration`：专门表示时间长度的字符串类型，支持 `h/m/s/ms/ns` 单位，可组合，`"1h30m"` 等价于 `"90m"`

这几个不是新的字面值语法，是官方文档里给参数标类型时用的记号，实际写配置时还是用 array/object 字面量。

## 字符串：标准 vs 原始

**标准字符串**（双引号）支持转义序列：`\\`（反斜杠）、`\n`（换行）、`\t`（制表符）、`\uNNNN`（Unicode 字符）。

**原始字符串**（反引号包裹）不做任何转义，所见即所得，适合写正则、Windows 路径这种反斜杠密集的内容：

```alloy
`Hello, "world"!`
```

原始字符串支持天然多行，换行会被原样保留：

```alloy
`Hello,
"world"!`
```

## Array / Object 的写法细节

数组允许尾随逗号（方便版本控制里 diff 干净）：

```alloy
[0, 1, 2, 3]

[
  0,
  1,
  2,
]
```

对象的 key 如果是合法标识符可以不加引号，否则必须用双引号包起来（常见于 Kubernetes 标签这种带 `.`、`/` 的 key）：

```alloy
{
  first_name = "John",
  last_name  = "Doe",
}

{
  "app.kubernetes.io/name"     = "mysql",
  "app.kubernetes.io/instance" = "mysql-abcxyz",
  namespace                    = "default",
}
```

## 两个特殊类型

### Secret

一种特殊字符串类型，专门给密码、token、API key 用——**Alloy 永远不会在日志/UI/debug 输出里明文展示它**，即使你手滑打印出来也是脱敏的。需要拿到明文字符串参与运算时，用 `convert.nonsensitive()` 显式转换（转换后就没有脱敏保护了，谨慎用）。

### Capsule

`capsule("<INTERNAL_NAME>")` 格式，代表 Alloy 内部专用的类型，比如某个组件导出的"接收器句柄"。不同 capsule 类型之间互不兼容，只有同一种内部类型才能互相传递——这也是为什么组件间"连线"必须按文档说的类型对齐，不能随便塞一个字符串进去：

```alloy
prometheus.remote_write "default" {
  endpoint {
    url = "http://localhost:9090/api/v1/write"
  }
}

prometheus.scrape "default" {
  targets    = [/* ... */]
  forward_to = [prometheus.remote_write.default.receiver]   // receiver 就是一个 capsule 类型
}
```

`forward_to` 只接受 `prometheus.remote_write` 导出的 receiver capsule，你没法传一个普通字符串或者别的组件的 capsule 进去，Alloy 在类型检查阶段就会拒绝。

## 小结

日常写配置基本只会用到 number/string/bool/array/object 这五种字面值。Secret 和 Capsule 不是自己手写字面量的类型，而是组件导出值天然带的类型标记——理解它们主要是为了看懂"为什么这个值不能直接打印"、"为什么这两个组件接口对不上"这类报错。

## 相关笔记

- [[监控告警链路追踪/Alloy/Alloy 配置语法入门.md]] — Block/Attribute/Component/Expression
- [[监控告警链路追踪/Alloy/Alloy 组件配置规则.md]] — 参数校验、依赖图
