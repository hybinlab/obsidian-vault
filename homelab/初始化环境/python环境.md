---
publish: true
---
**1. 系统 python（备用，一行搞定）**

```bash
apt install -y python3 python3-pip
```


---

**2. 安装 Miniconda**

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

安装过程中：

* 许可证一路回车/yes
* 安装路径默认 `~/miniconda3` 即可
* 最后问是否 `conda init` → **yes**

```bash
source ~/.bashrc
```


---

**3. 常用命令**

```bash
conda create -n myenv python=3.11   # 创建环境
conda activate myenv                 # 激活
conda deactivate                     # 退出
conda env list                       # 查看所有环境
conda install numpy                  # 装包
pip install xxx                      # conda没有的包用pip装
```


---

**4. 验证**

```bash
conda --version
python --version  # 激活环境后应显示conda管理的版本
```