import yaml
import numpy as np
from typing import Dict, Any, Optional


def format_degradation_result(result: Any, media_type: str) -> Dict:
    """
    格式化降质处理结果，便于前端展示

    Args:
        result: 处理后的媒体数据（图像数组或视频帧列表）
        media_type: 媒体类型（"image" 或 "video"）

    Returns:
        格式化后的结果字典
    """
    if media_type == "image":
        # 图像：返回形状和数据类型信息（实际部署时可返回Base64编码）
        return {
            "type": "image",
            "shape": result.shape,
            "dtype": str(result.dtype),
            "message": "图像降质处理完成"
        }
    else:
        # 视频：返回帧数和单帧形状信息
        return {
            "type": "video",
            "frame_count": len(result),
            "frame_shape": result[0].shape if result else None,
            "message": "视频降质处理完成"
        }


def load_degradation_config() -> Dict[str, Any]:
    """加载降质配置文件（degradation_config.yaml）"""
    with open("config/degradation_config.yaml", "r") as f:
        return yaml.safe_load(f)


def get_supported_degradations(media_type: str) -> List[str]:
    """获取指定媒体类型支持的所有降质类型"""
    config = load_degradation_config()
    return config["DEGRADATION_TYPES"][media_type]["common"] + \
        config["DEGRADATION_TYPES"][media_type]["advanced"]
