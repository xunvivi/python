import cv2
import numpy as np
from core.base_degradation import BaseDegradation


class DirtDegradation(BaseDegradation):
    """污点效应退化（支持自定义颜色）"""
    # 新增 spot_color 到允许的参数列表
    allowed_params = ['num_spots', 'size_range', 'darkness', 'spot_size', 'spot_color']

    def validate_params(self):
        """验证并处理参数"""
        # 1. 污点数量（非负整数）
        self.params['num_spots'] = max(0, int(self.params.get('num_spots', 5)))

        # 2. 污点大小（优先spot_size，兼容size_range）
        if 'spot_size' in self.params:
            spot_size = int(self.params['spot_size'])
            self.params['spot_size'] = max(1, spot_size)
            self.params['size_range'] = [self.params['spot_size'], self.params['spot_size']]
        else:
            size_range = self.params.get('size_range', [5, 20])
            if len(size_range) != 2 or size_range[0] > size_range[1]:
                raise ValueError("size_range必须是[min, max]格式的列表")
            size_range[0] = max(1, int(size_range[0]))
            size_range[1] = max(size_range[0], int(size_range[1]))
            self.params['size_range'] = size_range
            self.params['spot_size'] = size_range[0]

        # 3. 暗度（0-1范围）
        darkness = self.params.get('darkness', 0.6)
        self.params['darkness'] = max(0.0, min(1.0, float(darkness)))

        # 4. 污点颜色（新增参数验证）
        # 支持格式：(R, G, B)元组、整数（灰度）或预定义名称（如"black", "brown"）
        default_color = (0, 0, 0)  # 默认黑色
        spot_color = self.params.get('spot_color', default_color)

        # 预定义常用污点颜色（泥土色、灰色等）
        color_map = {
            'black': (0, 0, 0),
            'brown': (70, 40, 10),
            'gray': (100, 100, 100),
            'dark_brown': (40, 20, 5)
        }

        # 解析颜色参数
        if isinstance(spot_color, str):
            # 若为字符串，尝试从预定义颜色中匹配
            spot_color = spot_color.lower()
            if spot_color in color_map:
                spot_color = color_map[spot_color]
            else:
                raise ValueError(f"不支持的颜色名称: {spot_color}，支持: {list(color_map.keys())}")
        elif isinstance(spot_color, (int, float)):
            # 若为数字，视为灰度值（转为三通道）
            c = int(max(0, min(255, spot_color)))
            spot_color = (c, c, c)
        elif isinstance(spot_color, (tuple, list)):
            # 若为元组/列表，视为(R, G, B)，确保每个通道在0-255
            if len(spot_color) != 3:
                raise ValueError("spot_color元组必须包含3个元素（R, G, B）")
            spot_color = tuple([int(max(0, min(255, x))) for x in spot_color])
        else:
            raise TypeError(f"spot_color必须是字符串、数字或三元素元组，实际为: {type(spot_color)}")

        self.params['spot_color'] = spot_color

    def apply(self, data: np.ndarray) -> np.ndarray:
        """应用污点效果（支持自定义颜色）"""
        result = data.copy()
        h, w = result.shape[:2]
        spot_color = self.params['spot_color']

        for _ in range(self.params['num_spots']):
            # 随机位置
            x = np.random.randint(0, w)
            y = np.random.randint(0, h)

            # 确定污点大小
            if self.params['spot_size'] > 0:
                size = self.params['spot_size']
            else:
                size = np.random.randint(
                    self.params['size_range'][0],
                    self.params['size_range'][1] + 1
                )

            # 计算透明度（基于darkness参数，0为完全透明，1为完全不透明）
            alpha = self.params['darkness']

            # 绘制带透明度的彩色污点
            overlay = result.copy()  # 创建叠加层
            cv2.circle(overlay, (x, y), size, spot_color, -1)  # 绘制实心圆
            # 融合叠加层与原图（实现半透明效果）
            cv2.addWeighted(overlay, alpha, result, 1 - alpha, 0, result)

        return result