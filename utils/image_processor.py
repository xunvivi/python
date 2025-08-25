import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional


class ImageProcessor:
    """图像处理工具类"""

    @staticmethod
    def load_image(file_path: str) -> np.ndarray:
        """加载图像并转换为RGB格式

        Args:
            file_path: 图像文件路径

        Returns:
            RGB格式的图像数组 (H, W, 3)，uint8类型
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"图像文件不存在: {file_path}")

        # 使用OpenCV加载图像（默认BGR格式）
        image = cv2.imread(file_path)
        if image is None:
            raise ValueError(f"无法加载图像: {file_path}")

        # 转换为RGB格式
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    @staticmethod
    def save_image(image: np.ndarray, output_path: str) -> None:
        """保存RGB格式图像

        Args:
            image: RGB格式的图像数组 (H, W, 3)
            output_path: 输出文件路径
        """
        # 验证图像格式
        if len(image.shape) != 3 or image.shape[2] != 3:
            raise ValueError("输入必须是3通道RGB图像")

        # 转换为BGR格式保存
        bgr_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, bgr_image)

    @staticmethod
    def get_image_info(image: np.ndarray) -> dict:
        """获取图像信息

        Args:
            image: RGB格式的图像数组

        Returns:
            包含图像信息的字典
        """
        h, w, c = image.shape
        return {
            "width": w,
            "height": h,
            "channels": c,
            "dtype": str(image.dtype),
            "min_value": image.min(),
            "max_value": image.max()
        }
