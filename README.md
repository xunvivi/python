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
- **核心函数**：
  - 抽象基类 `BaseDegradation`，包含抽象方法 `apply()`（所有退化处理必须实现）
  - 通用参数验证方法 `validate_params()`（被子类继承）
  - 退化处理元数据管理（如支持的媒体类型、参数范围等）

#### composite_degradation.py
- **功能**：提供复合退化处理的基础支持，扩展 `DegradationPipeline` 的底层实现
- **核心函数**：
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

### 6. app.py
以下是各接口的前端请求参数格式及后端返回结果格式说明，基于提供的代码实现：

## 1. 单个降质处理接口 `/api/single-degradation`

### 前端请求参数
- **请求方式**：`POST`
- **Content-Type**：`application/json`
- **参数结构**：
  ```json
  {
    "media_path": "example.jpg",  // 必选，媒体文件在file目录下的相对路径
    "media_type": "image",        // 必选，媒体类型，只能是"image"或"video"
    "degradation_type": "blur",   // 必选，退化类型（参考DEGRADATION_CLASSES）
    "params": {                   // 可选，退化参数（根据类型动态变化）
      "kernel_size": 5,
      "sigma": 1.0
    }
  }
  ```

### 后端返回格式
```json
{
  "status": "success",
  "data": {
    "original_path": "/absolute/path/to/example.jpg",  // 原始文件绝对路径
    "processed_path": "/absolute/path/to/processed/example_blur.jpg",  // 处理后文件路径
    "degradation_types": ["blur"],  // 应用的退化类型
    "original_size": 123456,        // 原始文件大小（字节）
    "processed_size": 78901         // 处理后文件大小（字节）
  }
}
```


## 2. 文件上传接口 `/api/upload`
### 前端请求参数
- **请求方式**：`POST`
- **Content-Type**：`multipart/form-data`
- **参数结构**：
  - 表单字段：`file`（必选，二进制文件流，支持图片/视频）

### 后端返回格式
```json
{
  "status": "success",
  "data": {
    "file_path": "example.mp4",    // 上传后在file目录下的相对路径
    "file_name": "example.mp4",    // 原始文件名
    "content_type": "video/mp4"    // 文件MIME类型
  }
}
```


## 3. 复合降质处理接口 `/api/composite-degradation`
### 前端请求参数
- **请求方式**：`POST`
- **Content-Type**：`application/json`
- **参数结构**：
  ```json
  {
    "media_path": "example.png",
    "media_type": "image",
    "first_config": {
      "name": "noise",
      "params": {"noise_type": "gaussian", "intensity": 0.2}
    },
    "second_config": {
      "name": "compression",
      "params": {"quality": 50, "format": "jpeg"}
    },
    "third_config": {  // 可选
      "name": "blur",
      "params": {"kernel_size": 3}
    }
  }
  ```

### 后端返回格式
```json
{
  "status": "success",
  "data": {
    "original_path": "/absolute/path/to/example.png",
    "processed_path": "/absolute/path/to/processed/example_composite.jpg",
    "degradation_types": ["noise", "compression", "blur"],  // 按顺序的退化类型
    "status": "success"
  }
}
```


## 4. 获取媒体信息接口 `/api/media-info`
### 前端请求参数
- **请求方式**：`POST`
- **Content-Type**：`application/json`
- **参数结构**：
  ```json
  {
    "file_path": "example.mp4"  // 必选，file目录下的相对路径
  }
  ```

### 后端返回格式
```json
{
  "width": 1920,           // 宽度（像素）
  "height": 1080,          // 高度（像素）
  "format": "mp4",         // 文件格式
  "duration": 120.5,       // 时长（秒，视频）
  "fps": 30.0,             // 帧率（视频）
  "video_codec": "h264",   // 视频编码器
  "audio_codec": "aac",    // 音频编码器（视频）
  "bitrate": 2500000,      // 比特率（bps）
  "color_space": "yuv420p",// 色彩空间
  "bit_depth": 8,          // 位深
  "file_size": 37500000,   // 文件大小（字节）
  "file_size_human": "36.0MB",  // 人类可读大小
  "file_path": "example.mp4"
}
```


## 5. 获取文件接口 `/api/file`
### 前端请求参数
- **请求方式**：`GET`
- **查询参数**：`path`（必选，file目录下的相对路径，如`"processed/example.jpg"`）

### 后端返回格式
- 返回文件二进制流（`application/octet-stream`），浏览器可直接下载或预览。


## 6. 获取文件列表接口 `/api/file-list`
### 前端请求参数
- **请求方式**：`POST`
- **Content-Type**：`application/json`
- **参数结构**：
  ```json
  {
    "subdir": "processed"  // 可选，子目录名，默认为根目录
  }
  ```

### 后端返回格式
```json
{
  "status": "success",
  "data": {
    "current_dir": "processed",  // 当前目录
    "parent_dir": "",            // 父目录（空表示根目录）
    "files": [
      {
        "name": "example_blur.jpg",
        "path": "processed/example_blur.jpg",  // 相对路径
        "type": "image",                       // 类型（image/video）
        "size": 123456,                        // 大小（字节）
        "size_human": "120KB",                 // 人类可读大小
        "modified": 1690000000.0               // 最后修改时间（时间戳）
      },
      // ...更多文件
    ]
  }
}
```


## 7. 删除文件接口 `/api/files/delete`
### 前端请求参数
- **请求方式**：`POST`
- **Content-Type**：`application/json`
- **参数结构**：
  ```json
  {
    "file_path": "processed/example.jpg"  // 必选，file目录下的相对路径
  }
  ```

### 后端返回格式
```json
{
  "status": "success",
  "message": "文件已删除: processed/example.jpg"
}
```



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
