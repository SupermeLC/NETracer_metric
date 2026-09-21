# NETracer Metric

这是 NETracer（ICCV 2025）提出的三项迭代追踪指标的独立、可审计实现：

| 指标 | 衡量内容 | 趋势 |
|---|---|---:|
| PE（Position Error） | 匹配节点的局部位置精度 | 越低越好 |
| ABL（Average Branch Length） | 重建分支的连续性 | 越高越好 |
| JE（Jump Error） | 跳到相邻错误分支的拓扑错误 | 越低越好 |

完整定义、公式、边界条件、命令行和 Python API 请阅读
[英文主 README](README.md)。

## 安装与快速使用

```bash
git clone https://github.com/SupermeLC/NETracer_metric.git
cd NETracer_metric
python -m pip install -e .

netracer-metrics pair gold.swc prediction.swc
```

批量评测使用包含 `case_id,gold,test` 三列的 CSV：

```bash
netracer-metrics batch manifest.csv --output-dir results
```

## 三个指标的核心理解

**PE**：对每个预测节点寻找最近 gold 节点，只统计距离严格小于
`epsilon` 的匹配。它衡量“已经靠近标注的节点到底有多准”。必须同时查看
`matched_fraction`，因为未匹配节点不会进入 PE 平均值。

**ABL**：预测图的总边长除以“根节点数 + 分叉节点数”。它衡量典型分支能
连续追踪多远。ABL 不检查分支是否走对，因此必须结合 PE 和 JE 解读。

**JE**：将预测节点及其父节点映射到 gold 图。如果两个匹配点空间上很近，
但沿 gold 图的路径距离远大于直线距离，就说明预测边从一条分支跳到了邻近
分支，记一次 Jump Error。

## 重要复现说明

公开补充材料与旧实验代码并不完全一致：旧 PE 使用点到边距离和硬编码阈值
5，旧 JE 还有补充材料中未写出的绝对距离条件。本仓库默认严格实现公开算法，
差异详见 [协议说明](docs/protocol-notes.md)。因此，在复现旧论文表格前必须先
明确采用“公开算法协议”还是“旧代码兼容协议”。

仓库只包含合成样例和一个很小的 ROAD 坐标裁剪，不包含原图、完整标注或
大规模原始数据。
