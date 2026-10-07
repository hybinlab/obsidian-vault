## 环境管理

| 命令 | 说明 |
|----|----|
| `uv venv` | 创建虚拟环境（默认 `.venv/`） |
| `uv venv --python 3.11` | 指定 Python 版本创建环境 |
| `source .venv/bin/activate` | 激活虚拟环境 |
| `deactivate` | 退出虚拟环境 |

## 包管理

| 命令 | 说明 |
|----|----|
| `uv pip install <pkg>` | 安装包 |
| `uv pip install -r requirements.txt` | 从文件批量安装 |
| `uv pip uninstall <pkg>` | 卸载包 |
| `uv pip list` | 列出已安装包 |
| `uv pip freeze` | 导出依赖列表 |
| `uv pip show <pkg>` | 查看包详情 |

## 运行

| 命令 | 说明 |
|----|----|
| `uv run <script.py>` | 直接运行脚本 |

## 典型工作流

```bash
# 克隆开源项目后
git clone <repo>
cd <repo>
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```