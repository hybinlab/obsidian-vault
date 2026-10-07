---
publish: true
tags:
  - 渗透测试
  - 后渗透与提权
---
可在CMD窗口输入powershell打开一个新的powershell窗口

 ![](渗透测试笔记/uploads/e6d1e924-6404-478c-b58a-1a046b0538c8/8e247e1c-75ce-419d-a00d-626dc3bfc01a/image.png " =841x184")


## get-command

__列出当前PowerShell__会话中所有可用的 cmdlet、函数、别名和脚本

例如，如果我们只想显示类型为"function"的可用命令，可以使用`-CommandType "Function"`如下所示的语句：

```powershell
PS C:\Users\captain> Get-Command -CommandType "Function"

CommandType     Name                                               Version    Source                                                                                                                                     
-----------     ----                                               -------    ------
Function        A:
Function        Add-BCDataCacheExtension                           1.0.0.0    BranchCache
Function        Add-DnsClientDohServerAddress                      1.0.0.0    DnsClient
Function        Add-DnsClientNrptRule                              1.0.0.0    DnsClient
[...]
```


\
## Find-Module

__在PowerShell__ Gallery等在线存储库中搜索模块（cmdlet 集合）

有时，如果我们不知道模块的确切名称，搜索名称相似的模块会很有用。我们可以通过筛选 \`.\` 属性`Name`并在模块的部分名称后附加通配符 ( `*`\`)\` 来实现这一点，使用以下标准 PowerShell 语法：`Cmdlet -Property "pattern*`

```powershell
PS C:\Users\captain> Find-Module -Name "PowerShell*"   

Version    Name                                Repository           Description 
-------    ----                                ----------           ----------- 
0.4.7      powershell-yaml                     PSGallery            Powershell module for serializing and deserializing YAML

2.2.5      PowerShellGet                       PSGallery            PowerShell module with commands for discovering, installing, updating and publishing the PowerShell artifacts like Modules, DSC Resources, Role Capabilities and Scripts.                                                   
1.0.80.0   PowerShell.Module.InvokeWinGet      PSGallery            Module to Invoke WinGet and parse the output in PSOjects

0.17.0     PowerShellForGitHub                 PSGallery            PowerShell wrapper for GitHub API  
```

一旦确定了模块，就可以从存储库下载并安装这些模块`Install-Module`，从而使模块中包含的新 cmdlet 可供使用。

```powershell
PS C:\Users\captain> Install-Module -Name "PowerShellGet"

Untrusted repository
You are installing the modules from an untrusted repository. If you trust this repository, change its InstallationPolicy value by running the Set-PSRepository cmdlet. Are you sure you want to install the modules from 'PSGallery'?
[Y] Yes  [A] Yes to All  [N] No  [L] No to All  [S] Suspend  [?] Help (default is "N"): 
```


\
## Get-ChildItem

列出指定位置（由`-Path`参数指定）中的文件和目录。它可用于浏览目录并查看其内容。如果未`Path`指定参数，则该 cmdlet 将显示当前工作目录的内容。


## Set-Location

它会更改当前目录，将我们带到指定的路径，类似于`cd`命令


```powershell
PS C:\Users\captain> Set-Location -Path ".\Documents"
PS C:\Users\captain\Documents> 
```


## New-Item

__要在PowerShell__中创建项目，我们可以使用`New-Item`。我们需要指定项目的路径及其类型（是文件还是目录）

```powershell
PS C:\Users\captain\Documents> New-Item -Path ".\captain-cabin\captain-wardrobe" -ItemType "Directory"

    Directory: C:\Users\captain\Documents\captain-cabin

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----          9/4/2024  12:20 PM                captain-wardrobe

PS C:\Users\captain\Documents> New-Item -Path ".\captain-cabin\captain-wardrobe\captain-boots.txt" -ItemType "File"     

    Directory: C:\Users\captain\Documents\captain-cabin\captain-wardrobe

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----          9/4/2024  11:46 AM              0 captain-boots.txt  
```


## Remove-Item

会同时删除目录和文件

```powershell
PS C:\Users\captain\Documents> Remove-Item -Path ".\captain-cabin\captain-wardrobe\captain-boots.txt"
PS C:\Users\captain\Documents> Remove-Item -Path ".\captain-cabin\captain-wardrobe" 
```


## Copy-Item

复制或移动文件和目录

```powershell
PS C:\Users\captain\Documents> Copy-Item -Path .\captain-cabin\captain-hat.txt -Destination .\captain-cabin\captain-hat2.txt
PS C:\Users\captain\Documents> Get-ChildItem -Path ".\captain-cabin\" 

    Directory: C:\Users\captain\Documents\captain-cabin

Mode                 LastWriteTime         Length Name 
----                 -------------         ------ ----
d-----          9/4/2024  12:50 PM                captain-wardrobe
-a----          9/4/2024  12:50 PM              0 captain-boots.txt
-a----          9/4/2024  12:14 PM            264 captain-hat.txt
-a----          9/4/2024  12:14 PM            264 captain-hat2.txt
-a----          9/4/2024  12:37 PM           2116 ship-flag.txt 
```


## Get-Content

类似于`type`命令提示符（或`cat`）中的命令

```powershell
PS C:\Users\captain\Documents\captain-cabin> Get-Content -Path ".\captain-hat.txt"
 _           _   
| |         | |
| |__   __ _| |_
| '_ \ / _ | __|
| | | | (_| | |_
|_| |_|\__,_|\__|

Don't touch my hat!
```


## 管道符

允许将一个命令的输出作为另一个命令的输入

例如，如果想获取目录中的文件列表并按大小排序，可以在__PowerShell__中使用以下命令：

```powershell
PS C:\Users\captain\Documents\captain-cabin> Get-ChildItem | Sort-Object Length

    Directory: C:\Users\captain\Documents\captain-cabin

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----          9/4/2024  12:50 PM              0 captain-boots.txt
-a----          9/4/2024  12:14 PM            264 captain-hat2.txt
-a----          9/4/2024  12:14 PM            264 captain-hat.txt
-a----          9/4/2024  12:37 PM           2116 ship-flag.txt
d-----          9/4/2024  12:50 PM                captain-wardrobe
```


要根据指定条件筛选对象，仅返回符合条件的对象，我们可以使用 cmdlet `Where-Object`。例如，要仅列出`.txt`目录中的文件，我们可以使用：

```powershell
PS C:\Users\captain\Documents\captain-cabin> Get-ChildItem | Where-Object -Property "Extension" -eq ".txt" 

    Directory: C:\Users\captain\Documents\captain-cabin

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----          9/4/2024  12:50 PM              0 captain-boots.txt
-a----          9/4/2024  12:14 PM            264 captain-hat.txt
-a----          9/4/2024  12:14 PM            264 captain-hat2.txt
-a----          9/4/2024  12:37 PM           2116 ship-flag.txt
```

这里，`Where-Object`按文件属性筛选文件`Extension`，确保只列出扩展名等于 ( `-eq`) 的文件。`.txt`

该运算符`-eq`（即"**等于**"）是与其他脚本语言（例如 Bash、Python）共享的一组**比较运算符的一部分。为了展示**__PowerShell__筛选功能的潜力，列表中选择了一些最常用的运算符：

* `-ne`：**不等于**。此运算符可用于根据指定条件从结果中排除对象。
* `-gt`**大于**：此运算符将仅筛选出大于指定值的对象。需要注意的是，这是一个严格比较，这意味着等于指定值的对象将从结果中排除。
* `-ge`**大于或等于**。这是前一个运算符的非严格版本。它是"与"的`-gt`组合`-eq`。
* `-lt`"**小于**"运算符。与"大于"运算符类似，这是一个严格运算符。它只会包含严格小于某个特定值的对象。
* `-le`：**小于或等于**。与它的对应运算符一样`-ge`，这​​是前一个运算符的非严格版本。它是`-lt`and的组合`-eq`。

`-like`下面的另一个示例表明，还可以通过选择与指定模式匹配的属性来筛选对象：

```powershell
PS C:\Users\captain\Documents\captain-cabin> Get-ChildItem | Where-Object -Property "Name" -like "ship*"  

    Directory: C:\Users\captain\Documents\captain-cabin

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----          9/4/2024  12:37 PM           2116 ship-flag.txt
```


`Select-Object`用于从对象中选择特定属性或限制返回的对象数量。它对于精简输出，仅显示所需详细信息非常有用。

```powershell
PS C:\Users\captain\Documents\captain-cabin> Get-ChildItem | Select-Object Name,Length 

Name              Length
----              ------
captain-wardrobe
captain-boots.txt 0
captain-hat.txt   264
captain-hat2.txt  264
ship-flag.txt     2116
```


\
## Get-ComputerInfo

可以检索全面的系统信息，包括操作系统信息、硬件规格、BIOS 详情等等

```powershell
PS C:\Users\captain> Get-ComputerInfo

WindowsBuildLabEx                                       : 20348.859.amd64fre.fe_release_svc_prod2.220707-1832
WindowsCurrentVersion                                   : 6.3
WindowsEditionId                                        : ServerDatacenter
WindowsInstallationType                                 : Server Core
WindowsInstallDateFromRegistry                          : 4/23/2024 6:36:29 PM
WindowsProductId                                        : 00454-60000-00001-AA763
WindowsProductName                                      : Windows Server 2022 Datacenter
[...]
```


## Get-LocalUser

列出系统上的所有本地用户帐户

```powershell
PS C:\Users\captain> Get-LocalUser

Name               Enabled Description 
----               ------- -----------
Administrator      True    Built-in account for administering the computer/domain
captain            True    The beloved captain of this pirate ship.
DefaultAccount     False   A user account managed by the system.
Guest              False   Built-in account for guest access to the computer/domain
WDAGUtilityAccount False   A user account managed and used by the system for Windows Defender Application Guard scenarios.
```


## `Get-NetIPConfiguration`

供系统网络接口的详细信息，包括 IP 地址、__DNS__服务器和网关配置(不如直接用IPconfig)

```powershell
PS C:\Users\captain> Get-NetIPConfiguration

InterfaceAlias       : Ethernet
InterfaceIndex       : 5
InterfaceDescription : Amazon Elastic Network Adapter
NetProfile.Name      : Network 3
IPv4Address          : 10.10.178.209
IPv6DefaultGateway   :
IPv4DefaultGateway   : 10.10.0.1
DNSServer            : 10.0.0.2
```


## Get-NetIPAddress

显示系统上配置的所有 IP 地址的详细信息，包括当前未激活的 IP 地址。

```powershell
PS C:\Users\captain> Get-NetIPAddress

IPAddress         : fe80::3fef:360c:304:64e%5
InterfaceIndex    : 5
InterfaceAlias    : Ethernet
AddressFamily     : IPv6
Type              : Unicast
PrefixLength      : 64
PrefixOrigin      : WellKnown
SuffixOrigin      : Link
AddressState      : Preferred
ValidLifetime     : Infinite ([TimeSpan]::MaxValue)
PreferredLifetime : Infinite ([TimeSpan]::MaxValue)
SkipAsSource      : False
PolicyStore       : ActiveStore

IPAddress         : ::1
InterfaceIndex    : 1
InterfaceAlias    : Loopback Pseudo-Interface 1
AddressFamily     : IPv6
[...]

IPAddress         : 10.10.178.209
InterfaceIndex    : 5
InterfaceAlias    : Ethernet
AddressFamily     : IPv4
[...]
```


## Get-Process

提供当前所有运行进程的详细视图，包括__CPU__和内存使用情况

```powershell
PS C:\Users\captain> Get-Process

Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id  SI ProcessName 
-------  ------    -----      -----     ------     --  -- -----------
     67       5      872        500       0.06   2340   0 AggregatorHost
     55       5      712       2672       0.02   3024   0 AM_Delta_Patch_1.417.483.0
    309      13    18312       1256       0.52   1524   0 amazon-ssm-agent
     78       6     4440        944       0.02    516   0 cmd
     94       7     1224       1744       0.31    568   0 conhost
[...]
```


## Get-Service

检索有关计算机上服务状态的信息

```powershell
PS C:\Users\captain> Get-Service

Status   Name               DisplayName                           
------   ----               -----------
Stopped  Amazon EC2Launch   Amazon EC2Launch
Running  AmazonSSMAgent     Amazon SSM Agent
Stopped  AppIDSvc           Application Identity
Running  BFE                Base Filtering Engine
Running  CertPropSvc        Certificate Propagation
Stopped  ClipSVC            Client License Service (ClipSVC)
[...]
```


## Get-NetTCPConnection

显示当前__TCP__连接，从而深入了解本地和远程端点

```powershell
PS C:\Users\captain> Get-NetTCPConnection

LocalAddress        LocalPort RemoteAddress       RemotePort State       AppliedSetting OwningProcess 
------------        --------- -------------       ---------- -----       -------------- -------------
[...]
::                  22        ::                  0          Listen                     1444          
10.10.178.209       49695     199.232.26.172      80         TimeWait                   0
0.0.0.0             49668     0.0.0.0             0          Listen                     424
0.0.0.0             49667     0.0.0.0             0          Listen                     652
0.0.0.0             49666     0.0.0.0             0          Listen                     388
0.0.0.0             49665     0.0.0.0             0          Listen                     560
0.0.0.0             49664     0.0.0.0             0          Listen                     672           
0.0.0.0             3389      0.0.0.0             0          Listen                     980
10.10.178.209       139       0.0.0.0             0          Listen                     4
0.0.0.0             135       0.0.0.0             0          Listen                     908
10.10.178.209       22        10.14.87.60         53523      Established Internet       1444
0.0.0.0             22        0.0.0.0             0          Listen                     1444
```


## Get-FileHash

用于生成文件哈希值的实用 cmdlet，这在事件响应、威胁搜寻和恶意软件分析中特别有价值，因为它有助于验证文件完整性并检测潜在的篡改。

```powershell
PS C:\Users\captain\Documents\captain-cabin> Get-FileHash -Path .\ship-flag.txt    

Algorithm       Hash                      Path 
---------       ----                      ----
SHA256          54D2EC3C12BF3D[...]       C:\Users\captain\Documents\captain-cabin\ship-flag.txt
```


## Invoke-Command(重要)

 ![](渗透测试笔记/uploads/e6d1e924-6404-478c-b58a-1a046b0538c8/8764869f-5d9f-49e3-8bfb-0263681b8084/image.png " =1116x107")