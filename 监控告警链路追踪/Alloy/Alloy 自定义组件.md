---
publish: true
---

前面所有笔记用到的都是 Alloy 自带的内置组件（`local.file`、`prometheus.scrape` 之类）。这篇讲怎么把一堆内置组件打包成一个**自己的组件**，在配置里当一个整体复用。

## 是什么

> "Custom components allow you to package a pipeline of built-in and other custom components into a single, reusable unit."

本质是把 [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] 里那种"一堆组件靠引用连起来的链路"，封装成一个新的、可以像内置组件一样声明、引用、开多个 label 实例的东西。好处是团队内的通用处理模式（比如"给日志加统一标签再发走"）写一次，到处 `use`，不用每个配置文件都复制一遍那一长串 `loki.process` 链。

## 三个核心要素

- **Argument（参数）**：自定义组件对外暴露的输入，调用方传值进来
- **Export（导出）**：自定义组件对外暴露的输出，供外部引用
- **内部组件集合**：自定义组件内部实际跑的一串内置/自定义组件，组成内部管道

## 用 `declare` 定义

```alloy
declare "add" {
    argument "a" {
        comment  = "First number to add"
        optional = false
    }

    argument "b" {
        comment  = "Second number to add"
        optional = false
    }

    export "sum" {
        value = argument.a.value + argument.b.value
    }
}

add "example" {
    a = 15
    b = 17
}

// 引用导出值：add.example.sum == 32
```

拆解一下这个例子：

- `declare "add" { ... }` 声明了一个新组件类型，名字叫 `add`
- 块内部用 `argument "a" { ... }` / `argument "b" { ... }` 定义两个输入参数，`optional = false` 表示必填，`comment` 是给这个参数的说明（跟内置组件文档里的参数说明是一个道理）
- 内部逻辑通过 `argument.a.value`、`argument.b.value` 拿到调用方传进来的值参与运算
- `export "sum" { value = ... }` 定义一个输出值
- 定义完之后，`add "example" { a = 15  b = 17 }` 就是在**使用**这个自定义组件了，写法和用内置组件一模一样（组件名+label+参数），`add.example.sum` 就能像引用内置组件导出值一样引用到

## 和内置组件的关系：控制器一视同仁

组件控制器（[[监控告警链路追踪/Alloy/Alloy 组件控制器与生命周期.md]] 讲过的那个）不区分自定义组件和内置组件，统一走同一套生命周期：求值参数 → 执行内部组件 → 更新导出 → 上报健康状态。也就是说自定义组件一样有 Healthy/Unhealthy 状态、一样支持多 label 实例、一样参与依赖图的增量求值。

## Module：跨文件共享自定义组件

单个配置文件里 `declare` 的组件只在这个文件内可见。如果想让多个配置文件复用同一个自定义组件，要用 `import.file`（或 `import.git`/`import.http`/`import.string`）——具体语法见 [[监控告警链路追踪/Alloy/Alloy 顶层配置块参考.md]]。

## 适用场景

- 团队里有多个 Alloy 配置实例，都需要同一套"日志打标签+过滤"逻辑 → 封装成一个自定义组件，各处 `use`，改动只需要改一处
- 把一段复杂的多阶段 pipeline（比如模式三：日志采集→解析→富化→输出）收进一个自定义组件里，让顶层配置文件读起来更像"搭积木"而不是一堆细节

不需要用自定义组件的情况：配置内容简单、没有跨文件/跨团队复用需求——直接写内置组件链就够了，没必要为了"看起来更整洁"去额外封装一层。

## 小结

`declare` 定义自定义组件，内部用 `argument`/`export` 管理输入输出，中间塞一段内置组件组成的 pipeline；定义完之后使用方式和调用内置组件完全一样。核心价值是复用，不是必需品——只有真的要在多处复用同一段处理逻辑时才值得封装。

## 相关笔记

- [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] — 内部管道怎么搭
- [[监控告警链路追踪/Alloy/Alloy 组件控制器与生命周期.md]] — 自定义组件同样遵循的生命周期
- [[监控告警链路追踪/Alloy/Alloy 组件配置规则.md]] — 参数/导出的基础规则
