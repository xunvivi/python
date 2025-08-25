import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from utils.image_processor import ImageProcessor
from utils.video_processor import VideoProcessor
from utils.file_io import generate_output_filename
from single_main import load_degradation_class, DEGRADATION_CLASSES

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DegradationPipeline:
    """退化处理管道，用于组合多种退化处理"""

    def __init__(self, degradation_configs: List[Dict]):
        """初始化退化管道

        Args:
            degradation_configs: 退化配置列表，每个配置包含 'name' 和 'params'

        Raises:
            ValueError: 当配置无效或退化类加载失败时
        """
        self.degradations = []
        self._validate_and_load_degradations(degradation_configs)

    def _validate_and_load_degradations(self, configs: List[Dict]) -> None:
        """验证并加载所有退化处理类"""
        if not isinstance(configs, list):
            raise ValueError("退化配置必须是列表类型")

        for idx, config in enumerate(configs):
            # 验证配置结构
            if not isinstance(config, dict):
                raise ValueError(f"第{idx + 1}个退化配置必须是字典类型")
            if 'name' not in config:
                raise ValueError(f"第{idx + 1}个退化配置缺少必要的'name'字段")

            deg_type = config['name']
            deg_params = config.get('params', {})

            # 验证参数类型
            if not isinstance(deg_params, dict):
                raise ValueError(f"{deg_type}的参数必须是字典类型")

            try:
                # 处理复合退化类型
                if deg_type == "composite":
                    # 解析复合退化中的子退化类型
                    for sub_type, sub_params in deg_params.items():
                        # 检查子退化类型是否受支持
                        if sub_type not in DEGRADATION_CLASSES:
                            raise ValueError(
                                f"不支持的子退化类型: {sub_type}，支持的类型: {list(DEGRADATION_CLASSES.keys())}")

                        # 处理可能嵌套的 params 结构
                        if isinstance(sub_params, dict) and 'params' in sub_params and len(sub_params) == 1:
                            # 如果子参数被包装在 params 中，提取出来
                            actual_params = sub_params['params']
                        else:
                            actual_params = sub_params

                        sub_deg_class = load_degradation_class(sub_type)
                        self.degradations.append(sub_deg_class(actual_params))
                        logger.info(f"添加复合退化子处理[{len(self.degradations)}]: {sub_type}")
                else:
                    # 处理单一退化类型
                    # 处理可能嵌套的 params 结构
                    if isinstance(deg_params, dict) and 'params' in deg_params and len(deg_params) == 1:
                        actual_params = deg_params['params']
                    else:
                        actual_params = deg_params

                    deg_class = load_degradation_class(deg_type)
                    self.degradations.append(deg_class(actual_params))
                    logger.info(f"添加退化处理[{idx + 1}]: {deg_type}")

            except Exception as e:
                raise ValueError(f"加载退化处理'{deg_type}'失败: {str(e)}") from e

    def apply(self, data: Any) -> Any:
        """应用所有退化处理

        Args:
            data: 输入数据（图像或视频帧）

        Returns:
            处理后的数据

        Raises:
            RuntimeError: 当处理过程中出现错误时
        """
        result = data
        for idx, deg in enumerate(self.degradations, 1):
            try:
                result = deg.apply(result)
                if result is None:
                    raise RuntimeError(f"第{idx}个退化处理({deg.__class__.__name__})返回空结果")
            except Exception as e:
                raise RuntimeError(
                    f"第{idx}个退化处理({deg.__class__.__name__})执行失败"
                ) from e
        return result


def _ensure_output_dir() -> None:
    """确保输出目录存在，不存在则创建"""
    output_dir = Path("processed")
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建输出目录: {output_dir.absolute()}")


def process_image_with_pipeline(image_path: str, pipeline: DegradationPipeline) -> str:
    """使用退化管道处理图像

    Args:
        image_path: 图像路径
        pipeline: 退化处理管道

    Returns:
        处理后的图像路径
    """
    logger.info(f"开始处理图像: {image_path}")

    # 加载图像
    image = ImageProcessor.load_image(image_path)
    if image is None:
        raise ValueError(f"无法加载图像: {image_path}")

    # 应用退化管道
    processed_image = pipeline.apply(image)

    # 确保输出目录存在
    _ensure_output_dir()

    # 生成输出路径并保存
    output_filename = generate_output_filename(image_path, "composite")
    output_path = str(Path("processed") / output_filename)
    ImageProcessor.save_image(processed_image, output_path)

    logger.info(f"图像处理完成，保存至: {output_path}")
    return output_path


def process_video_with_pipeline(video_path: str, pipeline: DegradationPipeline) -> str:
    """使用退化管道处理视频

    Args:
        video_path: 视频路径
        pipeline: 退化处理管道

    Returns:
        处理后的视频路径
    """
    logger.info(f"开始处理视频: {video_path}")

    # 读取视频
    frames, video_info = VideoProcessor.read_video(video_path)
    if not frames:
        raise ValueError(f"无法读取视频帧: {video_path}")
    if not video_info or "fps" not in video_info:
        raise ValueError(f"视频信息不完整: {video_info}")

    # 应用退化管道到每一帧
    processed_frames = VideoProcessor.process_video_frames(frames, pipeline.apply)

    # 确保输出目录存在
    _ensure_output_dir()

    # 生成输出路径并保存
    output_filename = generate_output_filename(video_path, "composite")
    output_path = str(Path("processed") / output_filename)
    VideoProcessor.write_video(processed_frames, output_path, fps=video_info["fps"])

    logger.info(f"视频处理完成，保存至: {output_path}")
    return output_path


def composite_main_demo(
        media_path: str,
        media_type: str,
        first_config: Dict,
        second_config: Dict,
        third_config: Optional[Dict] = None
) -> Dict[str, Any]:
    """复合退化处理演示主函数

    Args:
        media_path: 媒体文件路径
        media_type: 媒体类型 ("image" 或 "video")
        first_config: 第一个退化配置
        second_config: 第二个退化配置
        third_config: 第三个退化配置（可选）

    Returns:
        处理结果字典
    """
    try:
        # 验证媒体文件存在性
        media_path = os.path.abspath(media_path)
        if not os.path.exists(media_path):
            raise FileNotFoundError(f"媒体文件不存在: {media_path}")

        # 验证媒体类型
        media_type = media_type.lower()
        if media_type not in ("image", "video"):
            raise ValueError(f"不支持的媒体类型: {media_type}，支持的类型: image, video")

        # 收集并验证所有退化配置
        degradation_configs: List[Dict] = []
        for config in [first_config, second_config, third_config]:
            if config is not None:
                degradation_configs.append(config)

        if len(degradation_configs) < 2:
            raise ValueError("至少需要提供两个退化配置")

        # 创建退化处理管道
        pipeline = DegradationPipeline(degradation_configs)

        # 根据媒体类型处理
        if media_type == "image":
            processed_path = process_image_with_pipeline(media_path, pipeline)
        else:  # video
            processed_path = process_video_with_pipeline(media_path, pipeline)

        return {
            "original_path": media_path,
            "processed_path": processed_path,
            "degradation_types": [config['name'] for config in degradation_configs],
            "status": "success"
        }

    except Exception as e:
        error_msg = f"复合处理失败: {str(e)}"
        logger.error(error_msg)
        raise  # 保留原始异常堆栈，方便调试
