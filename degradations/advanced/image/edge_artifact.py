import cv2
import numpy as np
from core.base_degradation import BaseDegradation


class EdgeArtifactDegradation(BaseDegradation):
    """边缘伪影退化（图像专属）"""
    # 新增 kernel_size 到允许的参数列表，解决参数不支持错误
    allowed_params = ['strength', 'kernel_size']

    def validate_params(self):
        """验证并处理参数"""
        # 1. 验证强度参数（0-1范围）
        strength = self.params.get('strength', 0.5)
        self.params['strength'] = max(0.0, min(1.0, float(strength)))  # 转为Python float

        # 2. 验证核大小参数（用于边缘检测的高斯核）
        kernel_size = self.params.get('kernel_size', 3)
        kernel_size = int(kernel_size)
        # 确保核大小是正奇数（3,5,7...），避免偶数导致的不对称
        if kernel_size <= 0:
            kernel_size = 3
        if kernel_size % 2 == 0:
            kernel_size += 1  # 偶数自动转为奇数
        self.params['kernel_size'] = kernel_size

    def apply(self, data: np.ndarray) -> np.ndarray:
        """
        应用边缘伪影效果（支持自定义核大小）

        Args:
            data: 输入RGB图像 (H, W, 3), uint8

        Returns:
            带边缘伪影的图像
        """
        strength = self.params['strength']
        kernel_size = self.params['kernel_size']

        # 转换为灰度图进行边缘检测
        gray = cv2.cvtColor(data, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150).astype(np.float32) / 255.0
        edges = np.expand_dims(edges, axis=2)  # 扩展维度以匹配RGB图像

        # 使用指定大小的核进行高斯模糊（影响边缘伪影的范围）
        blurred = cv2.GaussianBlur(
            data.astype(np.float32),
            (kernel_size, kernel_size),  # 使用自定义核大小
            sigmaX=1.5  # 固定sigma值，或可改为参数控制
        )

        # 生成边缘增强效果
        artifact = (data.astype(np.float32) - blurred) * strength * edges
        result = data.astype(np.float32) + artifact

        return np.clip(result, 0, 255).astype(np.uint8)
