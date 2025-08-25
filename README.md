# 图像/视频降质可视化系统

## 项目结构

```
python/
├── app.py                     # 前端接口

├── single_main.py             # 单种退化处理核心逻辑
├── composite_main.py          # 复合退化处理核心逻辑

├── core/                      # 核心退化处理框架
│   ├── base_degradation.py    # 退化处理基类
│   ├── composite_degradation.py # 复合退化处理基类
│   ├── stage1_degradation.py  # 第一阶段退化处理
│   ├── stage2_degradation.py  # 第二阶段退化处理
│   └── stage3_degradation.py  # 第三阶段退化处理

├── degradations/              # 具体退化处理实现
│   ├── advanced/              # 高级退化处理
│   │   ├── image/             # 图像专属退化
│   │   └── video/             # 视频专属退化
│   ├── common/                # 通用退化处理
│   │   └── blur.py            # 模糊退化处理（已完成）
│   │   └── noise.py           # 噪声退化处理（已完成）

├── utils/                     # 工具类模块
│   ├── api_utils.py           # API相关工具函数
│   ├── file_io.py             # 文件IO操作工具
│   ├── image_processor.py     # 图像处理工具
│   ├── video_processor.py     # 视频处理工具
│   └── visualization.py       # 可视化工具

├── file/                      # 媒体文件存储目录
│   └── processed/             # 处理后文件存储目录
└── config/                    # 配置文件目录
```

## 核心模块说明

### 1. core/ 目录 - 核心退化框架

退化处理的基础架构和分阶段处理逻辑，所有退化处理的底层支持。

#### base_degradation.py
- **功能**：定义所有退化处理类的基类，提供统一接口规范
- **核心内容**：
  - 抽象基类 `BaseDegradation`，包含抽象方法 `apply()`（所有退化处理必须实现）
  - 通用参数验证方法 `validate_params()`（被子类继承）
  - 退化处理元数据管理（如支持的媒体类型、参数范围等）

#### composite_degradation.py
- **功能**：提供复合退化处理的基础支持，扩展 `DegradationPipeline` 的底层实现
- **核心内容**：
  - 复合退化组合逻辑
  - 退化处理顺序优化算法
  - 处理结果缓存机制

#### stage1_degradation.py/stage2_degradation.py/stage3_degradation.py
- **功能**：按处理阶段划分的退化处理集合（按复杂度或处理顺序划分）
- **示例**：
  - 第一阶段（stage1）：基础退化（如模糊、噪声）
  - 第二阶段（stage2）：中等复杂度退化（如压缩、重采样）
  - 第三阶段（stage3）：高级退化（如运动模糊、闪烁）

### 2. degradations/ - 具体退化实现

该目录按退化类型和适用媒体类型分类，包含所有具体的退化处理算法。

#### degradations/common/ - 通用退化（图像和视频均适用）
- **模糊处理文件**：
  - `blur.py`：模糊退化处理
    - 类 `BlurDegradation`，实现 `apply()` 方法
    - 支持参数：`blur_type`（模糊类型）、`kernel_size`（核大小）、`sigma`（高斯标准差）
    - 方法 `validate_params()` 确保参数有效性（如核大小为正奇数）

### 3. utils/ - 工具函数

提供各类辅助功能，包括文件IO、图像处理、视频处理等工具函数，支持退化处理的各个环节。

### 4. file/ 目录 - 媒体文件存储

用于存储原始媒体文件和处理后的文件，其中 `processed/` 子目录专门存放处理结果。

### 5. config/ 目录 - 配置文件

存放系统配置参数，包括默认退化参数、路径配置等。

## 核心模块关系说明

### 1. 退化处理类的继承关系
- 所有具体退化处理类（如 `BlurDegradation`）继承自 `core/base_degradation.py` 中的基类
- 复合退化处理 `DegradationPipeline` 依赖 `core/composite_degradation.py` 的底层支持

### 2. 调用流程
- API 接口（`app.py`）接收请求后，根据处理类型调用 `single_main.py` 或 `composite_main.py`
- 退化处理类通过 `single_main.py` 中的 `load_degradation_class` 动态加载
- 媒体处理过程中，工具类（`image_processor.py`/`video_processor.py`）提供底层读写和帧处理能力

### 3. 配置与参数传递
- 默认参数由 `single_main.py` 中的 `validate_degradation_params` 定义，可被配置文件覆盖
- 复合退化配置通过 `DegradationPipeline` 解析
