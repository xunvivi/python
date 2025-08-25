import numpy as np
from core.base_degradation import BaseDegradation


class InterlaceDegradation(BaseDegradation):
    """隔行扫描效应退化（图像专属）"""
    allowed_params = ['intensity']

    def validate_params(self):
        """验证并处理参数"""
        intensity = self.params.get('intensity', 0.5)
        self.params['intensity'] = np.clip(intensity, 0, 1)

    def apply(self, data: np.ndarray) -> np.ndarray:
        """
        应用隔行扫描效果

        Args:
            data: 输入RGB图像 (H, W, 3), uint8

        Returns:
            带隔行扫描效果的图像
        """
        intensity = self.params['intensity']
        result = data.astype(np.float32)

        # 随机选择奇偶行进行亮度衰减
        keep_odd = np.random.random() > 0.5
        start_row = 1 if keep_odd else 0

        # 对选定行应用衰减
        result[start_row::2] *= (1 - intensity)

        return np.clip(result, 0, 255).astype(np.uint8)
