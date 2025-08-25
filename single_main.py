import os
from pathlib import Path
from typing import Dict, Any
import logging

from utils.image_processor import ImageProcessor
from utils.video_processor import VideoProcessor
from utils.file_io import save_uploaded_file, generate_output_filename

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 退化处理类映射表 - 用于动态加载退化处理
DEGRADATION_CLASSES = {
    # 通用退化
    "blur": "degradations.common.blur.BlurDegradation",
    "noise": "degradations.common.noise.NoiseDegradation",
    "resample": "degradations.common.resample.ResampleDegradation",
    "compression": "degradations.common.compression.CompressionDegradation",
    # 图像专属退化
    "aliasing": "degradations.advanced.image.aliasing.AliasingDegradation",
    "scratch": "degradations.advanced.image.scratch.ScratchDegradation",
    "dirt": "degradations.advanced.image.dirt.DirtDegradation",
    "interlace": "degradations.advanced.image.interlace.InterlaceDegradation",
    "edge_artifact": "degradations.advanced.image.edge_artifact.EdgeArtifactDegradation",
    # 视频专属退化
    "motion_blur": "degradations.advanced.video.motion_blur.MotionBlurDegradation",
    "flicker": "degradations.advanced.video.flicker.FlickerDegradation",
    "shake":"degradations.advanced.video.shake.ShakeDegradation"
}


def load_degradation_class(degradation_type: str):
    """动态加载退化处理类

    Args:
        degradation_type: 退化类型名称

    Returns:
        退化处理类
    """
    if degradation_type not in DEGRADATION_CLASSES:
        raise ValueError(f"不支持的退化类型: {degradation_type}，支持的类型: {list(DEGRADATION_CLASSES.keys())}")

    # 解析类路径
    module_path, class_name = DEGRADATION_CLASSES[degradation_type].rsplit('.', 1)

    # 动态导入模块和类
    import importlib
    try:
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except ImportError as e:
        logger.error(f"无法导入退化处理模块 {module_path}: {str(e)}")
        raise ImportError(f"退化处理模块 {module_path} 不存在或导入失败")
    except AttributeError as e:
        logger.error(f"退化处理类 {class_name} 在模块 {module_path} 中不存在: {str(e)}")
        raise AttributeError(f"退化处理类 {class_name} 不存在")


def process_image(image_path: str, degradation_type: str, params: Dict) -> str:
    """处理图像

    Args:
        image_path: 图像路径
        degradation_type: 退化类型
        params: 退化参数

    Returns:
        处理后的图像路径
    """
    logger.info(f"开始处理图像: {image_path}, 退化类型: {degradation_type}")

    try:
        # 验证输入文件
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")

        # 加载图像
        image = ImageProcessor.load_image(image_path)
        if image is None:
            raise ValueError(f"无法加载图像: {image_path}")

        # 加载并实例化退化处理类
        degradation_class = load_degradation_class(degradation_type)
        degradation = degradation_class(params)

        # 应用退化处理
        processed_image = degradation.apply(image)
        if processed_image is None:
            raise RuntimeError(f"退化处理失败: {degradation_type}")

        # 生成输出路径
        output_filename = generate_output_filename(image_path, degradation_type)

        # 确保输出目录存在
        output_dir = Path("processed")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / Path(output_filename).name)

        # 保存处理后的图像
        ImageProcessor.save_image(processed_image, output_path)

        # 验证输出文件是否成功创建
        if not os.path.exists(output_path):
            raise RuntimeError(f"图像保存失败: {output_path}")

        logger.info(f"图像处理完成，保存至: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"图像处理失败: {str(e)}")
        raise


def process_video(video_path: str, degradation_type: str, params: Dict) -> str:
    """处理视频

    Args:
        video_path: 视频路径
        degradation_type: 退化类型
        params: 退化参数

    Returns:
        处理后的视频路径（已优化为浏览器兼容格式）
    """
    logger.info(f"开始处理视频: {video_path}, 退化类型: {degradation_type}")

    try:
        # 验证输入文件
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 读取视频
        frames, video_info = VideoProcessor.read_video(video_path)
        if not frames:
            raise ValueError(f"无法读取视频帧: {video_path}")

        logger.info(f"视频信息: {video_info}")

        # 加载并实例化退化处理类
        degradation_class = load_degradation_class(degradation_type)
        degradation = degradation_class(params)

        # 对每一帧应用退化处理
        logger.info(f"开始处理 {len(frames)} 帧视频...")
        processed_frames = VideoProcessor.process_video_frames(frames, degradation.apply)

        if not processed_frames:
            raise RuntimeError(f"视频帧处理失败: {degradation_type}")

        # 生成输出路径
        output_filename = generate_output_filename(video_path, degradation_type)

        # 确保输出目录存在
        output_dir = Path("processed")
        output_dir.mkdir(parents=True, exist_ok=True)
        final_output_path = str(output_dir / Path(output_filename).name)

        # 确保输出文件名以.mp4结尾（浏览器兼容性）
        if not final_output_path.endswith('.mp4'):
            final_output_path = os.path.splitext(final_output_path)[0] + '.mp4'

        # 使用增强的VideoProcessor保存视频（自动处理浏览器兼容性）
        fps = video_info.get("fps", 30.0)  # 默认30fps
        logger.info(f"使用 {fps} FPS 保存视频到: {final_output_path}")

        # 新的VideoProcessor.write_video已经内置了浏览器兼容性处理
        actual_output_path = VideoProcessor.write_video(processed_frames, final_output_path, fps=fps)

        # 验证输出文件是否成功创建
        if not os.path.exists(actual_output_path):
            raise RuntimeError(f"视频保存失败: {actual_output_path}")

        # 验证视频是否可播放
        if not VideoProcessor.verify_video_playable(actual_output_path):
            logger.warning(f"生成的视频可能无法正常播放: {actual_output_path}")

        logger.info(f"视频处理完成，最终输出: {actual_output_path}")
        return actual_output_path

    except Exception as e:
        logger.error(f"视频处理失败: {str(e)}")
        raise


def validate_degradation_params(degradation_type: str, params: Dict) -> Dict:
    """验证和标准化退化参数

    Args:
        degradation_type: 退化类型
        params: 输入参数

    Returns:
        验证后的参数字典
    """
    if not isinstance(params, dict):
        params = {}

    # 为不同退化类型设置默认参数
    default_params = {
        "blur": {"kernel_size": 5, "sigma": 1.0},
        "noise": {"noise_type": "gaussian", "intensity": 0.1},
        "resample": {"scale_factor": 0.5, "interpolation": "bilinear"},
        "compression": {"quality": 80, "format": "jpeg"},
        "aliasing": {"downsample_factor": 2},
        "scratch": {"num_scratches": 3, "intensity": 0.5},
        "motion_blur": {"blur_length": 10, "angle": 0},
        "flicker": {"intensity": 0.3, "frequency": 5}
    }

    # 合并默认参数和用户参数
    validated_params = default_params.get(degradation_type, {}).copy()
    validated_params.update(params)

    logger.info(f"退化参数验证完成: {degradation_type} -> {validated_params}")
    return validated_params


def single_main_demo(media_path: str, media_type: str, degradation_type: str, degradation_params: Dict = None) -> Dict[
    str, Any]:
    """单种退化处理演示主函数

    Args:
        media_path: 媒体文件路径
        media_type: 媒体类型 ("image" 或 "video")
        degradation_type: 退化类型
        degradation_params: 退化参数

    Returns:
        处理结果字典
    """
    # 参数验证
    if degradation_params is None:
        degradation_params = {}

    logger.info(f"开始单种退化处理: {media_path}, 类型: {media_type}, 退化: {degradation_type}")

    try:
        # 验证媒体文件存在
        if not os.path.exists(media_path):
            raise FileNotFoundError(f"媒体文件不存在: {media_path}")

        # 验证媒体类型
        if media_type not in ["image", "video"]:
            raise ValueError(f"不支持的媒体类型: {media_type}，支持的类型: image, video")

        # 验证退化类型
        if degradation_type not in DEGRADATION_CLASSES:
            raise ValueError(f"不支持的退化类型: {degradation_type}，支持的类型: {list(DEGRADATION_CLASSES.keys())}")

        # 验证退化参数
        validated_params = validate_degradation_params(degradation_type, degradation_params)

        # 获取文件大小信息
        original_size = os.path.getsize(media_path)
        logger.info(f"原始文件大小: {original_size / (1024 * 1024):.2f} MB")

        # 根据媒体类型处理
        if media_type == "image":
            processed_path = process_image(media_path, degradation_type, validated_params)
        elif media_type == "video":
            processed_path = process_video(media_path, degradation_type, validated_params)

        # 获取处理后文件信息
        processed_size = os.path.getsize(processed_path) if os.path.exists(processed_path) else 0
        logger.info(f"处理后文件大小: {processed_size / (1024 * 1024):.2f} MB")

        # 计算相对路径用于前端显示
        try:
            from utils.file_io import FILE_ROOT
            relative_original = os.path.relpath(media_path, FILE_ROOT)
            relative_processed = os.path.relpath(processed_path, FILE_ROOT)
        except Exception:
            relative_original = media_path
            relative_processed = processed_path

        result = {
            "original_path": relative_original,
            "processed_path": relative_processed,
            "full_original_path": media_path,
            "full_processed_path": processed_path,
            "degradation_type": degradation_type,
            "degradation_params": validated_params,
            "media_type": media_type,
            "original_size": original_size,
            "processed_size": processed_size,
            "status": "success",
            "message": f"{media_type}退化处理完成"
        }

        logger.info(f"退化处理成功完成: {degradation_type}")
        return result

    except Exception as e:
        error_msg = f"退化处理失败: {str(e)}"
        logger.error(error_msg, exc_info=True)

        return {
            "original_path": media_path,
            "processed_path": None,
            "degradation_type": degradation_type,
            "degradation_params": degradation_params,
            "media_type": media_type,
            "status": "error",
            "error": str(e),
            "message": error_msg
        }


# 便捷函数：批量退化处理
def batch_degradation_demo(media_files: list, degradation_configs: list) -> Dict[str, Any]:
    """批量退化处理演示

    Args:
        media_files: 媒体文件路径列表
        degradation_configs: 退化配置列表，每个配置包含 {media_type, degradation_type, params}

    Returns:
        批量处理结果
    """
    results = []
    successful = 0
    failed = 0

    logger.info(f"开始批量退化处理: {len(media_files)} 个文件, {len(degradation_configs)} 种配置")

    for media_file in media_files:
        for config in degradation_configs:
            try:
                result = single_main_demo(
                    media_path=media_file,
                    media_type=config.get("media_type", "image"),
                    degradation_type=config.get("degradation_type", "blur"),
                    degradation_params=config.get("params", {})
                )

                if result["status"] == "success":
                    successful += 1
                else:
                    failed += 1

                results.append(result)

            except Exception as e:
                failed += 1
                results.append({
                    "original_path": media_file,
                    "degradation_type": config.get("degradation_type", "unknown"),
                    "status": "error",
                    "error": str(e)
                })

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "success_rate": f"{(successful / len(results) * 100):.1f}%" if results else "0%"
        }
    }


if __name__ == "__main__":
    # 测试代码
    test_image_path = "test_files/sample.jpg"
    test_video_path = "test_files/sample.mp4"

    # 测试图像处理
    if os.path.exists(test_image_path):
        print("=== 测试图像退化处理 ===")
        result = single_main_demo(
            media_path=test_image_path,
            media_type="image",
            degradation_type="blur",
            degradation_params={"kernel_size": 7, "sigma": 2.0}
        )
        print(f"结果: {result}")

    # 测试视频处理
    if os.path.exists(test_video_path):
        print("\n=== 测试视频退化处理 ===")
        result = single_main_demo(
            media_path=test_video_path,
            media_type="video",
            degradation_type="motion_blur",
            degradation_params={"blur_length": 15, "angle": 45}
        )
        print(f"结果: {result}")

    print("\n=== 支持的退化类型 ===")
    for degradation_name in DEGRADATION_CLASSES.keys():
        print(f"- {degradation_name}")