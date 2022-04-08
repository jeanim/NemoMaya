# Nemo: an acceleration framework for Maya Rigging

💡 请务必设置环境变量NEMO_ROOT

> 对于Linux系统，需要在打开Maya前设置`LD_LIBRARY_PATH`到`<NEMO_ROOT>/lib/<os>-<MayaVersion>/`，注意在Maya.env中设置无效会被覆盖

- <NEMO_ROOT>/extern: 外部依赖
- <NEMO_ROOT>/modules: 解析Maya文件所需的配置文件
- <NEMO_ROOT>/nemo: 主体代码
- <NEMO_ROOT>/lib: 依赖的Nemo库

# Table of Contents
1. [导出](#导出)
2. [上传服务器处理](#服务器处理)
3. [本地组装](#组装)
4. [运行时](#运行时)
5. [检查](#检查)

## 导出

```python
import os
import sys
sys.path.insert(0, '{}/extern'.format(os.environ['NEMO_ROOT']))
sys.path.insert(0, '{}'.format(os.environ['NEMO_ROOT']))
platform = "windows" if cmds.about(windows=True) else "centos7"
version = cmds.about(version=True)
sys.path.insert(0, '{}/lib/{}-{}'.format(os.environ['NEMO_ROOT'], platform, version))
import nemo.interface.exporter as exporter
exporter.show()
```

在Maya导出工具中，用户可以配置选择控制器的策略，选择模型的组，启用内部插件。

同时用户也可以直接参考interface直接调用nemo.m2n中的方法，做更强的自定义。

> 第一次使用时可以把控制器的GLOB和输出的组分别设置为 ***Main_ctrl*** 和 ***Geometry|high|body***, 以便快速测试

导出成功后的文件：

- **Graph JSON** 描述了Rig的运算逻辑，即Maya节点图。注意Graph JSON中的节点命名是会脱敏处理的。
- Resource 是特殊的nemodata格式，它包含了模型，权重，修型等数据。
- Scene JSON 主要描述了控制器的数据。
- Debug JSON 使用户可以在本地[检查](#检查)效果错误及其具体原因

**只有 Graph JSON 需要发送到服务器处理**， 其它的文件会在后续组装文件时用到。

通过将项目相关的几何信息隔离到Resource文件中以及重命名脱敏，这些隐私数据将无需对外分享。

## 服务器处理

这块目前完全靠人工处理...

服务器回传的内容包括：

* Maya插件
* Config JSON

## 组装

```python
# ...
import nemo.interface.assembler as assembler
assembler.show()
```

收到服务器发送回的数据后，用户可以在本地重新组装成新的Maya文件。

主要用到的数据包括：
* 描述控制器的Scene JSON
* 存储了模型，权重，修型等数据的nemodata

组装完成后，工具将会把生成的Maya文件保存至指定的Runtime文件夹内。（注意这个文件夹会被工具清空）
还包括运行时所需的依赖文件

> 组装完是没有材质的，需要用户从原文件迁移。

## 运行时

动画师使用Rig时除了需要在组装阶段生成的maya文件之外，还包括：
* 与角色匹配的插件，不同的角色需使用不同的插件。当然，不同角色的插件可以同时加载。
* nemodata资源文件。这个资源文件的路径在maya文件中指明，属性名通常是`<your-rig-id>1.resource`

💡 Linux系统可以考虑在env中设置`__GL_SYNC_TO_VBLANK=0`, 会节省帧刷新时间

## 检查

如果用生成的Nemo Rig去替换动画文件中的原始Rig，可能会发送效果不匹配的情况，甚至直接崩溃。此时可以使用`NemoMayaNodes`插件中的NemoCheck命令检查错误。

NemoCheck命令使用原始Rig而非Nemo Rig，此命令会检查Nemo中所有节点的计算结果与Maya中是否匹配，并生成日志文件。

NemoCheck命令有两个参数，分别是[导出](#导出)的 Debug JSON 和 nemodata，除此之外的Flag包括：
* id(ignoreDeformer)        默认为开。因为变形器检查的时间很长，所以可以用此选项跳过所有的变形器
* ns(namespace)             默认为空。Rig的命名空间，不需要时可以留空
* od(outputDirectory)       默认为空。日志输出目录，为空时输出到 Script Editor
* s(skip)                   默认为空。可以跳过某个节点的检查，需要跳过多个节点时用`;`分隔
* v(verbose)                默认为0。日志的详细程度
* x(stopOnFirstError)       默认为开。在第一个错误时即停止而不是检查完所有节点才停止

### 使用方法
```python
cmds.loadPlugin("NemoMayaNodes.mll")
print cmds.NemoCheck(path_debug, path_resource, ns='<your-namespace>', od='<your-log-directory>')
```
如果有错误，生成的日志文件中会包含一些 closure JSON（闭包），这些 closure 记录了节点的输入和输出，用于开发者复现 Bug 进行调试。

由于变形器的输入可能包含资产数据，所以NemoCheck会选择最不匹配的一个点记录 closure，因此用户可以放心地将闭包与开发者共享。

### 命令崩溃时
如果 Nemo 替换后即崩溃，那么 NemoCheck 同样也可能运行即崩溃。这其实是一件好事，说明复现并捕捉到了错误。

此时可以选择将 verbose 设置为 1，并打开日志记录。日志中可以看到在哪个节点发生了崩溃。

将 verbose 设置为 2 时，NemoCheck 还会在检查前就为所有节点记录 closure，但这样会导致执行过程相当漫长，因此仅在必要时如此做。