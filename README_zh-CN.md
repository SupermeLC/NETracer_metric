# NETracer Metric

这是 NETracer（ICCV 2025）提出的三个追踪评估指标的独立实现。

| 指标 | 衡量内容 | 趋势 |
|---|---|---:|
| PE（Position Error） | 匹配节点的位置误差 | 越低越好 |
| ABL（Average Branch Length） | 预测分支的连续性 | 越高越好 |
| JE（Jump Error） | 从一条邻近分支跳到另一条分支的错误连接 | 越低越好 |

## 安装

```bash
git clone https://github.com/SupermeLC/NETracer_metric.git
cd NETracer_metric
python -m pip install -e .
```

## Python 快速开始

```python
from netracer_metrics import evaluate_files

result = evaluate_files(
    "examples/road_crop/gold.swc",
    "examples/road_crop/prediction.swc",
)

print(f"PE: {result.pe.value:.3f}")
print(f"Matched fraction: {result.pe.matched_fraction:.3f}")
print(f"ABL: {result.abl.value:.3f}")
print(f"JE: {result.je.value}")
```

预期输出：

```text
PE: 1.177
Matched fraction: 0.574
ABL: 47.416
JE: 0
```

使用自己的数据时只需替换路径：

```python
result = evaluate_files("gold.swc", "prediction.swc")
```

也可以直接从命令行运行：

```bash
python -m netracer_metrics pair gold.swc prediction.swc
```

## 指标解释

### PE — Position Error

PE 为每个预测节点寻找最近的 gold 节点。距离小于匹配阈值（默认 2）的
预测节点视为匹配，PE 是这些匹配节点距离的平均值。

PE 越低表示匹配节点的位置越准确。需要同时查看 `matched_fraction`：未匹配
节点不会进入 PE 平均值，因此只看 PE 不能判断覆盖率。

公开算法使用点到点距离，所以 SWC 节点的采样密度也会影响 PE。

### ABL — Average Branch Length

ABL 是预测图的总长度除以分支数量，用来表示预测分支能连续追踪多远。
ABL 越高通常表示连续性越好。

ABL 不使用 gold 图，因此长分支不一定是正确分支，需要结合 PE 和 JE 解读。

### JE — Jump Error

JE 检查预测图中的每条父子边，并把边的两个端点映射到 gold 图。如果两个
端点在空间中很近，但沿 gold 图需要走很远，说明预测可能从一条邻近分支跳到
了另一条分支，记作一次 Jump Error。

JE 越低越好。它是错误次数，因此不同方法必须在相同样本和预处理下比较。

## 输入要求

SWC 每行至少包含：

```text
id type x y z radius parent
```

gold 和 prediction 必须使用相同的坐标系和单位。二维数据令 `z = 0`，根节点
使用 `parent = -1`。

## 批量评测（可选）

需要评测多个样本时，创建 CSV：

```csv
case_id,gold,test
sample_01,gold/sample_01.swc,pred/sample_01.swc
sample_02,gold/sample_02.swc,pred/sample_02.swc
```

然后运行：

```bash
python -m netracer_metrics batch manifest.csv --output-dir results
```

程序会生成逐样本结果 `per_case.csv` 和数据集汇总 `summary.json`。

## 样例与复现说明

仓库只包含一个合成样例和一个很小的 ROAD 坐标裁剪，不包含原图、完整标注
或完整数据集。

本仓库默认实现论文补充材料中的公开算法。旧实验代码中的 PE 和 JE 存在一些
不同规则；需要复现历史实验表格时请阅读
[协议说明](docs/protocol-notes.md)。

英文主文档见 [README.md](README.md)。
