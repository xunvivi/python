import cv2
import numpy as np
from core.base_degradation import BaseDegradation


class ShakeDegradation(BaseDegradation):
    """抖动重影退化（支持位移、频率控制，适用于图像和视频）"""
    # 新增 displacement 参数到允许的列表
    allowed_params = ['max_offset', 'mix_weight', 'frequency', 'displacement']

    def __init__(self, params: dict = None):
        super().__init__(params)
        self.frame_counter = 0  # 帧计数器，用于频率控制

    def validate_params(self) -> None:
        """验证抖动参数的合法性（含位移参数）"""
        # 1. 验证最大偏移像素（兼容旧参数）
        max_offset = self.params.get('max_offset', 5)
        max_offset = int(max_offset)
        if max_offset < 1:
            raise ValueError(f"max_offset必须是正整数，当前值: {max_offset}")
        self.params['max_offset'] = max_offset

        # 2. 验证位移参数（新增，控制单次抖动的最大位移）
        # displacement 优先级高于 max_offset，用于更精细的位移控制
        displacement = self.params.get('displacement')
        if displacement is not None:
            displacement = int(displacement)
            if displacement < 1:
                raise ValueError(f"displacement必须是正整数，当前值: {displacement}")
            self.params['displacement'] = displacement
            # 用displacement覆盖max_offset，确保参数一致性
            self.params['max_offset'] = displacement
        else:
            # 若未传displacement，使用max_offset作为默认位移
            self.params['displacement'] = max_offset

        # 3. 验证混合权重
        mix_weight = self.params.get('mix_weight', 0.5)
        mix_weight = float(mix_weight)
        if not (0 < mix_weight < 1):
            raise ValueError(f"mix_weight必须在(0, 1)范围内，当前值: {mix_weight}")
        self.params['mix_weight'] = mix_weight

        # 4. 验证频率参数
        frequency = self.params.get('frequency', 0.0)
        frequency = float(frequency)
        if frequency < 0:
            raise ValueError(f"frequency不能为负数，当前值: {frequency}")
        self.params['frequency'] = frequency

    def apply(self, data: np.ndarray) -> np.ndarray:
        """应用抖动重影效果（结合位移和频率控制）"""
        # 优先使用displacement作为实际位移上限
        displacement = self.params['displacement']
        mix_weight = self.params['mix_weight']
        frequency = self.params['frequency']
        h, w = data.shape[:2]

        # 频率控制逻辑
        should_jitter = True
        if frequency > 0:
            frame_interval = max(1, int(30 / frequency))
            should_jitter = (self.frame_counter % frame_interval) == 0

        if not should_jitter:
            self.frame_counter += 1
            return data

        # 基于displacement生成随机位移（核心修改）
        dx = np.random.randint(-displacement, displacement + 1)
        dy = np.random.randint(-displacement, displacement + 1)

        # 应用位移变换
        transform_matrix = np.float32([[1, 0, dx], [0, 1, dy]])
        jittered = cv2.warpAffine(
            data,
            transform_matrix,
            (w, h),
            borderMode=cv2.BORDER_WRAP
        )

        # 混合原图和位移图
        result = cv2.addWeighted(
            data, mix_weight,
            jittered, 1 - mix_weight,
            gamma=0
        )

        self.frame_counter += 1
        return result

    def preprocess(self, data: np.ndarray) -> np.ndarray:
        if data.dtype in [np.float32, np.float64] and np.max(data) <= 1.0:
            return (data * 255).astype(np.uint8)
        return data