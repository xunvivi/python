import cv2
import numpy as np
import logging
from core.base_degradation import BaseDegradation

logger = logging.getLogger(__name__)


class ResampleDegradation(BaseDegradation):
    """下采样降质处理（先下采样再上采样回原尺寸）"""

    # 允许的参数列表
    allowed_params = ['scale_factor', 'interpolation']

    # 插值方式映射（OpenCV常量）
    INTERPOLATION_MAP = {
        'bilinear': cv2.INTER_LINEAR,
        'nearest': cv2.INTER_NEAREST,
        'bicubic': cv2.INTER_CUBIC,
        'area': cv2.INTER_AREA  # 推荐下采样使用
    }

    def validate_params(self) -> None:
        """验证下采样特定参数"""
        # 验证缩放因子（必须在(0, 1)之间）
        scale = self.params.get('scale_factor', 0.5)
        if not isinstance(scale, (int, float)) or not (0 < scale < 1):
            raise ValueError(f"scale_factor必须是(0, 1)之间的数字，当前值: {scale}")
        self.params['scale_factor'] = scale  # 确保参数被正确设置

        # 验证插值方式
        interp = self.params.get('interpolation', 'bilinear')
        if interp not in self.INTERPOLATION_MAP:
            raise ValueError(
                f"不支持的插值方式: {interp}，支持的方式: {list(self.INTERPOLATION_MAP.keys())}"
            )
        self.params['interpolation'] = interp  # 确保参数被正确设置

    def apply(self, data: np.ndarray) -> np.ndarray:
        """
        应用下采样降质

        Args:
            data: 输入图像或视频帧（numpy数组，形状为[H, W, C]）

        Returns:
            处理后的图像或视频帧
        """
        # 获取参数
        scale = self.params['scale_factor']
        interp_name = self.params['interpolation']
        interp = self.INTERPOLATION_MAP[interp_name]

        # 获取原始尺寸
        h, w = data.shape[:2]

        # 计算下采样尺寸（确保至少为1x1，避免cv2.resize报错）
        new_h = max(1, int(h * scale))
        new_w = max(1, int(w * scale))

        # 日志输出（便于调试）
        logger.debug(
            f"下采样处理 - 原始尺寸: {h}x{w}, "
            f"缩放因子: {scale}, "
            f"下采样尺寸: {new_h}x{new_w}, "
            f"插值方式: {interp_name}"
        )

        try:
            # 第一步：下采样到新尺寸
            downsampled = cv2.resize(data, (new_w, new_h), interpolation=interp)
            # 第二步：上采样回原始尺寸
            return cv2.resize(downsampled, (w, h), interpolation=interp)
        except Exception as e:
            logger.error(
                f"下采样处理失败（原始尺寸: {h}x{w}, 目标尺寸: {new_h}x{new_w}）: {str(e)}"
            )
            raise  # 抛出异常，让上层处理

    def preprocess(self, data: np.ndarray) -> np.ndarray:
        """预处理：确保数据格式正确"""
        # 如果是float类型且在[0,1]范围内，转换为[0,255]
        if data.dtype in [np.float32, np.float64] and np.max(data) <= 1.0:
            return (data * 255).astype(np.uint8)
        return data
