# Nemo: an acceleration framework for Maya Rigging

💡 请务必设置环境变量NEMO_ROOT

> 对于Linux系统，需要在打开Maya前设置`LD_LIBRARY_PATH`到`<NEMO_ROOT>/lib/<os>-<MayaVersion>/`，注意在Maya.env中设置无效会被覆盖

- <NEMO_ROOT>/extern: 外部依赖
- <NEMO_ROOT>/modules: 解析Maya文件所需的配置文件
- <NEMO_ROOT>/nemo: 主体代码
- <NEMO_ROOT>/lib: 依赖的Nemo库

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
- Debug JSON 使用户可以在本地检查效果错误及其具体原因

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

> 组装完是没有材质的，需要用户从原文件迁移。

## 运行时

Linux系统可以考虑在env中设置`__GL_SYNC_TO_VBLANK=0`

## 重要缺陷

- 遇到错误可能崩溃
