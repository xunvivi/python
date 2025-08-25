import cv2
import numpy as np
from core.base_degradation import BaseDegradation


class AliasingDegradation(BaseDegradation):
    """锯齿效应退化（支持图像和视频）"""
    # 新增 downsample_factor 到允许的参数列表
    allowed_params = ['scale_factor', 'downsample_factor']

    def validate_params(self):
        super().validate_params()

        # 1. 处理下采样因子（downsample_factor）和缩放因子（scale_factor）的兼容逻辑
        # 优先使用 downsample_factor（如2表示缩小到1/2）
        if 'downsample_factor' in self.params:
            downsample = float(self.params['downsample_factor'])
            # 确保下采样因子 >1（否则无锯齿效果）
            if downsample <= 1:
                raise ValueError("downsample_factor必须大于1（如2表示缩小到1/2）")
            self.params['downsample_factor'] = downsample
            # 自动计算对应的scale_factor（1/downsample_factor）
            self.params['scale_factor'] = 1.0 / downsample
        else:
            # 若未传downsample_factor，则使用scale_factor
            scale = self.params.get('scale_factor', 0.3)
            if not (0 < scale < 1):
                raise ValueError("scale_factor必须在(0, 1)范围内")
            self.params['scale_factor'] = scale
            # 自动计算对应的downsample_factor（用于日志显示）
            self.params['downsample_factor'] = 1.0 / scale

    def apply(self, data: np.ndarray) -> np.ndarray:
        """应用锯齿效应（通过最近邻插值放大缩小产生锯齿）"""
        scale = self.params['scale_factor']
        h, w = data.shape[:2]

        # 计算下采样尺寸（确保至少1x1）
        new_h = max(1, int(h * scale))
        new_w = max(1, int(w * scale))

        # 关键：使用最近邻插值（INTER_NEAREST）产生明显锯齿
        downsampled = cv2.resize(data, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        # 放大回原尺寸，继续使用最近邻插值增强锯齿效果
        result = cv2.resize(downsampled, (w, h), interpolation=cv2.INTER_NEAREST)

        return result