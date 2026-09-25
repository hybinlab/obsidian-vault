---
publish: true
---

承接 [[监控告警链路追踪/Alloy/Alloy 运算符.md]]，Expression 的第三种构成元素是函数调用（第四种是组件引用，前面笔记都覆盖过了）。

## 函数调用的求值流程

固定三步：

1. **求值参数**：所有实参从左到右先求值（意味着实参里可以嵌套别的函数调用/组件引用，会先被展开成具体值）
2. **类型检查**：校验实参类型是否匹配函数签名
3. **执行**：跑函数逻辑，返回单一值

任何一步失败（类型不对、函数内部报错），Alloy **直接停止处理整条表达式并报错**，不会静默吞掉错误或者返回一个默认值。

## 函数的两个来源

- **标准库函数**：Alloy 内置，写配置时可以直接调用，不需要额外声明
- **组件导出的函数**：某些组件除了导出普通值，也可以导出"函数"这种值，其他组件可以直接调用它

**没有自定义函数机制**——配置文件里不能自己写一个函数出来，只能用标准库现成的或者某个组件导出的。

## 标准库五大分类

| 分类 | 命名空间 | 用途 |
| --- | --- | --- |
| 系统函数 | `sys.*` | 和宿主机交互，比如读环境变量 |
| 编码函数 | `encoding.*` | JSON/YAML 等格式的编解码 |
| 字符串函数 | `string.*` | 文本格式化、拼接、分割 |
| 数组函数 | `array.*` | 集合/列表操作 |
| 类型转换函数 | `convert.*` | 数据类型互转（比如前面笔记提到的 `convert.nonsensitive` 给 Secret 脱敏转普通字符串） |

## 实际组合示例

从环境变量取值、拼路径：

```alloy
log_level = sys.env("LOG_LEVEL")
data_dir  = sys.env("DATA_PATH") + "/metrics"
```

解析文件内容（JSON/YAML）后取字段，再和 `string.format` 拼起来：

```alloy
config_data     = encoding.from_json(local.file.config.content)
metrics_config  = encoding.from_yaml(local.file.metrics.content)

service_name  = config_data["service"]["name"]
full_address  = config_data["host"] + ":" + string.format("%d", config_data["port"])

job_name = string.format("%s-%s", service_name, sys.env("ENVIRONMENT"))
log_file = string.join(["/var/log", service_name, "app.log"], "/")
```

用 `array.concat` 把多个组件发现出来的 target 列表拼成一个，外加手写的一条 target：

```alloy
all_targets = array.concat(
  discovery.kubernetes.services.targets,
  discovery.file.local.targets,
  [{ "__address__" = "localhost:9090" }]
)
```

## 组件导出的函数：不只是标准库

一个组件也可以导出"函数"给别的地方调用，比 [[监控告警链路追踪/Alloy/Alloy 组件配置规则.md]] 里讲的"导出一个值"更进一步——导出的是可执行逻辑：

```alloy
processed_targets = data_processor.custom.transform_targets(
  discovery.kubernetes.services.targets,
  { "environment" = sys.env("ENV"), "region" = "us-west-2" }
)

final_config = {
  "targets" = processed_targets,
  "labels"  = custom_labeler.instance.generate_labels(service_name) + base_labels,
  "enabled" = validator.config.is_valid(processed_targets) && sys.env("MONITORING_ENABLED") == "true"
}
```

这个例子里能看到函数调用、运算符（`+` 拼接、`&&`/`==` 逻辑判断）、组件引用三者混用拼出一个复杂的 object——这也是 Alloy 配置语言"可编程"的具体体现：不是简单的 key-value 静态配置，而是能在配置层做数据处理和条件判断。

## 小结

函数调用 = 标准库或组件导出的可执行逻辑，参数从左到右先求值、再类型检查、再执行，出错就整条表达式报错。日常最常用的是 `sys.env`（取环境变量）和 `encoding.from_json/from_yaml`（解析配置文件），复杂场景才会碰到组件导出函数。

## 相关笔记

- [[监控告警链路追踪/Alloy/Alloy 数据类型.md]] — 基础类型、Secret、Capsule
- [[监控告警链路追踪/Alloy/Alloy 运算符.md]] — 算术/比较/逻辑/访问运算符
- [[监控告警链路追踪/Alloy/Alloy 组件配置规则.md]] — 组件导出值、依赖图求值顺序
