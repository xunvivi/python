import numpy as np
from core.base_degradation import BaseDegradation


class FlickerDegradation(BaseDegradation):
    """闪烁效应退化（支持幅度、频率、强度多参数控制）"""
    # 新增 amplitude 到允许的参数列表
    allowed_params = ['range', 'intensity', 'frequency', 'amplitude']

    def __init__(self, params: dict = None):
        super().__init__(params)
        self.frame_counter = 0  # 帧计数器（用于频率控制）

    def validate_params(self):
        super().validate_params()

        # 1. 验证亮度范围（兼容旧逻辑，优先级低于amplitude）
        flicker_range = self.params.get('range', [0.5, 1.5])
        if len(flicker_range) != 2 or flicker_range[0] >= flicker_range[1]:
            raise ValueError("range必须是长度为2的递增列表（如[0.5, 1.5]）")
        self.params['range'] = flicker_range

        # 2. 验证强度参数（0-1，控制整体生效比例）
        intensity = self.params.get('intensity', 1.0)
        self.params['intensity'] = max(0.0, min(1.0, float(intensity)))

        # 3. 验证频率参数（每秒闪烁次数）
        frequency = self.params.get('frequency', 5.0)
        if frequency < 0:
            raise ValueError("frequency不能为负数")
        self.params['frequency'] = float(frequency)

        # 4. 验证幅度参数（新增，控制亮度波动幅度）
        # amplitude：相对于正常亮度的波动比例（如0.3表示±30%）
        amplitude = self.params.get('amplitude', 0.5)
        if amplitude < 0:
            raise ValueError("amplitude不能为负数")
        self.params['amplitude'] = float(amplitude)

    def apply(self, data: np.ndarray) -> np.ndarray:
        """应用闪烁效果（结合幅度、频率、强度控制）"""
        intensity = self.params["intensity"]
        frequency = self.params["frequency"]
        amplitude = self.params["amplitude"]
        h, w = data.shape[:2]

        # 频率控制：计算闪烁间隔
        frame_interval = max(1, int(30 / (frequency + 1e-6)))  # 基于30FPS
        should_flicker = (self.frame_counter % frame_interval) == 0

        # 幅度控制：基于amplitude计算实际波动范围（优先级高于range）
        # 正常亮度为1.0，波动范围为 [1-amplitude, 1+amplitude]
        base_min = max(0.1, 1.0 - amplitude)  # 最低不低于10%亮度
        base_max = min(2.0, 1.0 + amplitude)  # 最高不超过200%亮度
        # 结合intensity收缩范围
        adjusted_min = 1.0 - (1.0 - base_min) * intensity
        adjusted_max = 1.0 + (base_max - 1.0) * intensity

        # 随机闪烁区域
        margin_x, margin_y = int(w * 0.3), int(h * 0.3)
        x1 = np.random.randint(0, margin_x + 1)
        y1 = np.random.randint(0, margin_y + 1)
        x2 = np.random.randint(w - margin_x, w)
        y2 = np.random.randint(h - margin_y, h)

        # 应用闪烁效果
        result = data.astype(np.float32)
        if should_flicker:
            factor = np.random.uniform(adjusted_min, adjusted_max)
            result[y1:y2, x1:x2] *= factor

        # 帧计数递增
        self.frame_counter += 1
        return np.clip(result, 0, 255).astype(np.uint8)