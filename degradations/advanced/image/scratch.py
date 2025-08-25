import cv2
import numpy as np
from core.base_degradation import BaseDegradation


class ScratchDegradation(BaseDegradation):
    """划痕退化（图像/视频通用）"""
    # 新增 brightness 到允许的参数列表，解决参数不支持错误
    allowed_params = ['num_scratches', 'width_range', 'intensity', 'line_width', 'brightness']

    def validate_params(self):
        # 1. 验证划痕数量（非负整数）
        self.params['num_scratches'] = max(0, int(self.params.get('num_scratches', 10)))

        # 2. 验证线宽参数（优先使用line_width，兼容width_range）
        if 'line_width' in self.params:
            line_width = int(self.params['line_width'])
            self.params['line_width'] = max(1, line_width)  # 线宽至少为1
            self.params['width_range'] = [self.params['line_width'], self.params['line_width']]
        else:
            width_range = self.params.get('width_range', [1, 3])
            if len(width_range) != 2 or width_range[0] > width_range[1]:
                raise ValueError("width_range必须是[min, max]格式（如[1,3]）")
            width_range[0] = max(1, int(width_range[0]))
            width_range[1] = max(width_range[0], int(width_range[1]))
            self.params['width_range'] = width_range
            self.params['line_width'] = width_range[0]

        # 3. 验证强度参数（0-1范围，影响划痕可见度）
        intensity = self.params.get('intensity', 0.8)
        self.params['intensity'] = max(0.0, min(1.0, float(intensity)))

        # 4. 验证亮度参数（0-255范围，控制划痕颜色深浅）
        # 若未传入brightness，默认根据intensity计算（255 * intensity）
        brightness = self.params.get('brightness', None)
        if brightness is not None:
            # 限制亮度在0-255之间（确保是有效像素值）
            self.params['brightness'] = max(0, min(255, int(brightness)))
        else:
            # 自动计算默认亮度（与intensity关联）
            self.params['brightness'] = int(255 * self.params['intensity'])

    def apply(self, data: np.ndarray) -> np.ndarray:
        result = data.copy()
        h, w = result.shape[:2]
        # 获取划痕颜色（使用brightness参数，支持彩色和灰度图）
        color_value = self.params['brightness']

        # 生成多个划痕
        for _ in range(self.params['num_scratches']):
            # 随机起点和终点（确保在图像范围内）
            x1, y1 = np.random.randint(0, w), np.random.randint(0, h)
            x2, y2 = np.random.randint(0, w), np.random.randint(0, h)

            # 确定线宽
            if self.params['line_width'] > 0:
                line_width = self.params['line_width']
            else:
                line_width = np.random.randint(
                    self.params['width_range'][0],
                    self.params['width_range'][1] + 1
                )

            # 根据图像通道数设置颜色（彩色图为三通道，灰度图为单通道）
            if len(result.shape) == 3 and result.shape[2] == 3:  # 彩色图
                color = (color_value, color_value, color_value)
            else:  # 灰度图
                color = color_value

            # 绘制划痕
            cv2.line(
                img=result,
                pt1=(x1, y1),
                pt2=(x2, y2),
                color=color,
                thickness=line_width
            )

        return result
