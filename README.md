# ABAQUS INP 提取工具

从大型 INP 文件中提取指定子系统

---

## 📍 项目定位

### ABAQUS CAE的局限

ABAQUS/CAE在处理孤立网格时：
- 缺少几何体参考，无法使用图形化选择工具
- 集合操作（并集、交集）依赖几何查询，对孤立网格失效
- 大型模型（数千ELSET）手动操作易出错

### 从源文件筛选的优势

INP文件是结构化文本，包含完整的拓扑关系：
- 节点-单元-ELSET层级清晰
- 材料-截面-约束依赖明确
- 可通过名称或关键词精确匹配

### 本工具的作用

**工作流程**：
1. **解析INP文件** —— 识别主关键字块（NODE, ELEMENT, MATERIAL, SECTION, Constraint等）
2. **依赖跟踪** —— ELSET → 节点 → 材料 → 约束，递归收集完整依赖链
3. **批量生成** —— 按系统配置生成独立INP文件，保留拓扑顺序
4. **智能缓存** —— 自动检测文件修改，避免重复解析，支持批量提取多次调用

**提取内容（模型定义）**：
- 几何：节点（*NODE）、单元（*ELEMENT）
- 集合：NSET、ELSET、Surface
- 属性：材料（*MATERIAL）、截面（*SECTION）
- 连接：Connector Behavior
- 约束：Coupling、Rigid Body、MPC、Tie、Equation、Embedded Region 等

**不提取（分析定义）**：
- 边界条件（*BOUNDARY）
- 载荷（*CLOAD、*DLOAD、*PRESSURE）
- 分析步（*STEP）
- 输出请求（*OUTPUT、*NODE PRINT、*EL PRINT）
- 初始条件（*INITIAL CONDITIONS）

> 提取的 INP 文件包含完整的模型结构，可在 ABAQUS/CAE 中导入后添加边界条件和载荷进行分析

---

## 📁 项目结构

```
extract/
├── batch.py                        # 批量提取调度器
├── scripts/                        # 提取脚本
│   ├── extract.py                  # ELSET提取
│   ├── parse.py                    # INP解析
│   └── extractor.py                # 依赖跟踪
└── silverado/                      # 示范模型
    ├── silverado.inp               # 源文件
    ├── silverado.inp.cache.pkl     # 解析缓存
    ├── elsets.py                   # 待提取ELSET字典
    └── silverado_*.inp             # 提取后的子系统
```

**核心文件说明**：
- `batch.py` —— 批量提取多个系统
- `scripts/extract.py` —— 命令行提取指定 ELSET（支持单个或多个）
- `scripts/parse.py` —— 解析 INP 文件结构（识别节点、单元、材料等）
- `scripts/extractor.py` —— 收集完整依赖关系（自动包含材料、约束等）
- `silverado/elsets.py` —— 定义要提取哪些 ELSET（手动配置分组）

---

## 🚀 快速开始

### 处理你的 INP 文件

本工具支持常见的 ABAQUS INP 文件（HyperMesh / ANSA / PATRAN / GMSH 等前处理软件生成的孤立网格模型）。

**步骤 1：准备文件**
```bash
mkdir your_model
cp your_file.inp your_model/model.inp
```

**步骤 2：创建提取配置**

在 `your_model/elsets.py` 中定义要提取的 ELSET：
```python
SYSTEMS = {
    'system1': [
        'ELSET_NAME_1',
        'ELSET_NAME_2',
        # ... 添加需要的 ELSET
    ],
}
```

**步骤 3：提取**

```bash
# 命令行提取（单个或多个 ELSET）
python scripts/extract.py your_model/model.inp --elsets "ELSET1,ELSET2" -o output.inp

# 批量提取（多个系统）
python batch.py your_model/model.inp
```

---

## 💡 示范例子

以下使用 Silverado 整车模型（365MB，3000+ ELSET）演示实际效果。

### 命令行提取示例

```bash
# 提取单个 ELSET
python scripts/extract.py silverado/silverado.inp --elsets "P2000293;mc-disk" -o output.inp

# 提取多个 ELSET（逗号分隔）
python scripts/extract.py silverado/silverado.inp --elsets "P2000293;mc-disk,P2000016;13-bw-bodymnt-disk" -o brake.inp
```

**输出**：
```text
[目标] P2000293;mc-disk, P2000016;13-bw-bodymnt-disk
[单元] 1017个单元, 1089个节点
[约束] 2个约束
```

---

### 批量提取示例

**Silverado 配置文件**（`silverado/elsets.py`）：
```python
SYSTEMS = {
    'body': [151个ELSET],
    'brake': [6个ELSET],
    'powertrain': [56个ELSET],
    'steering': [11个ELSET],
    'suspension': [97个ELSET],
    'wheel': [25个ELSET],
}
```

**执行批量提取**：
```bash
python batch.py silverado/silverado.inp
```

**输出**：
```text
[批量提取] SILVERADO
[源文件] silverado/silverado.inp
[配置文件] F:\...\extract\silverado\elsets.py
----------------------------------------
  body                 151 个部件
  brake                  6 个部件
  powertrain            56 个部件
  steering              11 个部件
  suspension            97 个部件
  wheel                 25 个部件
----------------------------------------

[brake] 提取中...
  [目标] 6个ELSET: P2000016;13-bw-bodymnt-disk-middle, ...
  [单元] 1603个单元, 1710个节点
  [约束] 3个约束, 3个Nset
  [属性] 6个截面

[powertrain] 提取中...
  [目标] 56个ELSET: P2000121;101-bw-engineframesuprt, ...
  [单元] 31660个单元, 34709个节点
  [约束] 1250个约束, 90个Nset
  [属性] 56个截面

...

[完成] 批量提取完成
```

**生成文件**（与源文件同目录）：
```
silverado/
├── silverado_body.inp       (30MB, 225856单元)
├── silverado_brake.inp      (214KB, 1603单元)
├── silverado_powertrain.inp (4.7MB, 31660单元)
├── silverado_steering.inp   (256KB, 1743单元)
├── silverado_suspension.inp (3.2MB, 20557单元)
└── silverado_wheel.inp      (5.4MB, 41937单元)
```

---


## 🔧 扩展

### 添加新分组

在现有车型的 `elsets.py` 中添加新的系统分组：

```python
SYSTEMS = {
    # ... 原有分组
    'exhaust': [
        'P2000346;mc-exhaust-body',
        'P2000347;exhaust-pipe',
        # ... 手动添加需要的 ELSET
    ],
}
```

---

### 自定义组合分组

如果需要创建组合系统（如前桥 = 悬挂 + 车轮 + 转向 + 刹车），可以先定义基础列表，再组合：

```python
# 基础系统
_SUSPENSION = ['P2000144;20-fr-suspension...', ...]
_WHEEL = ['P2000143;19-fr-sparetiremount', ...]
_STEERING = ['P2000345;mc-steer-cylinder', ...]
_BRAKE = ['P2000016;13-bw-bodymnt-disk...', ...]

SYSTEMS = {
    'suspension': _SUSPENSION,
    'wheel': _WHEEL,
    'steering': _STEERING,
    'brake': _BRAKE,

    # 组合系统：前桥 = 悬挂 + 车轮 + 转向 + 刹车
    'front_axle': sorted(set(_SUSPENSION + _WHEEL + _STEERING + _BRAKE)),
}
```

---

## 📄 许可证

MIT License

---

## 📊 数据来源

本项目使用的 Silverado 整车模型来自 George Mason University 的开源数据：

**2007 Chevrolet Silverado Finite Element Model**
https://www.ccsa.gmu.edu/models/2007-chevrolet-silverado/

感谢 GMU Center for Collision Safety and Analysis (CCSA) 提供的高质量开源有限元模型。
