import cv2
import numpy as np
import math
from core.base_degradation import BaseDegradation


class MotionBlurDegradation(BaseDegradation):
    """运动模糊退化（仅适用于视频）"""
    allowed_params = ['kernel_size', 'angle']

    def validate_params(self):
        super().validate_params()

        # 确保核大小为奇数
        ks = self.params.get('kernel_size', 15)
        self.params['kernel_size'] = ks if ks % 2 == 1 else ks + 1

        # 确保角度在[0, 360)范围内
        angle = self.params.get('angle', 0)
        self.params['angle'] = angle % 360

    def apply(self, data: np.ndarray) -> np.ndarray:
        """应用运动模糊

        Args:
            data: RGB格式的视频帧 (H, W, 3)

        Returns:
            运动模糊后的视频帧
        """
        kernel_size = self.params['kernel_size']
        angle = self.params['angle']

        # 生成运动模糊核
        kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
        center = kernel_size // 2
        angle_rad = math.radians(angle)

        length = kernel_size // 2
        for i in range(-length, length + 1):
            x = int(center + i * math.cos(angle_rad))
            y = int(center + i * math.sin(angle_rad))
            if 0 <= x < kernel_size and 0 <= y < kernel_size:
                kernel[y, x] = 1

        # 避免全零核
        if np.sum(kernel) == 0:
            kernel[center, center] = 1
        else:
            kernel /= np.sum(kernel)

        return cv2.filter2D(data, -1, kernel)
