import numpy as np
import logging
from typing import Dict, Any, Optional, Type
from core.base_degradation import BaseDegradation

# 动态导入支持的降质类型（根据实际实现调整）
from degradations.aliasing import AliasingDegradation
from degradations.scratch import ScratchDegradation
from degradations.dirt import DirtDegradation
from degradations.interlace import InterlaceDegradation
from degradations.edge_artifact import EdgeArtifactDegradation
from degradations.motion_blur import MotionBlurDegradation
from degradations.flicker import FlickerDegradation
from degradations.shake import ShakeDegradation

# 配置日志
logger = logging.getLogger(__name__)

# 支持的第三阶段降质类型映射表
SUPPORTED_DEGRADATIONS = {
    'aliasing': AliasingDegradation,  # 锯齿失真
    'scratch': ScratchDegradation,  # 划痕损伤
    'dirt': DirtDegradation,  # 污点污染
    'interlace': InterlaceDegradation,  # 隔行扫描失真
    'edge_artifact': EdgeArtifactDegradation,  # 边缘伪影
    'motion_blur': MotionBlurDegradation,  # 运动模糊
    'flicker': FlickerDegradation,  # 闪烁噪声
    'shake': ShakeDegradation  # 抖动失真
}


class Stage3Degradation(BaseDegradation):
    """
    第三阶段降质处理类：可选的单一特殊降质类型

    用于模拟特定场景下的额外质量损伤，如传输错误、设备故障等
    一次只能选择一种降质类型应用
    """
    # 允许的参数：降质类型和对应参数
    allowed_params = ['degradation_type', 'params']

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化第三阶段降质处理器

        Args:
            params: 包含降质类型和参数的字典
                {
                    "degradation_type": str,  # 降质类型，必须是SUPPORTED_DEGRADATIONS中的key
                    "params": dict            # 对应降质类型的参数
                }
        """
        super().__init__(params)

        # 初始化降质处理器
        self._degrader = None
        self._degradation_type = None

    def validate_params(self) -> None:
        """验证第三阶段降质参数的合法性"""
        # 检查是否指定了降质类型
        if 'degradation_type' not in self.params:
            raise ValueError("第三阶段必须指定 'degradation_type' 参数")

        # 检查降质类型是否支持
        self._degradation_type = self.params['degradation_type']
        if self._degradation_type not in SUPPORTED_DEGRADATIONS:
            raise ValueError(
                f"不支持的降质类型: {self._degradation_type}, "
                f"支持的类型: {list(SUPPORTED_DEGRADATIONS.keys())}"
            )

        # 检查参数是否为字典
        if 'params' in self.params and not isinstance(self.params['params'], dict):
            raise ValueError("'params' 必须是字典类型")

    def _init_degrader(self) -> None:
        """初始化选中的降质处理器"""
        if self._degradation_type is None:
            raise ValueError("未初始化降质类型，请先调用validate_params")

        # 获取降质类并初始化
        deg_class: Type[BaseDegradation] = SUPPORTED_DEGRADATIONS[self._degradation_type]
        self._degrader = deg_class(self.params.get('params', {}))
        self._degrader.media_type = self.media_type

        logger.info(f"初始化第三阶段降质处理器: {self._degradation_type}")

    def apply(self, data: np.ndarray) -> np.ndarray:
        """
        应用第三阶段降质处理

        Args:
            data: 输入媒体数据（第二阶段处理后的输出）

        Returns:
            经过第三阶段降质处理后的媒体数据
        """
        if self._degrader is None:
            self._init_degrader()

        # 记录输入数据信息
        logger.info(
            f"第三阶段降质开始 - 类型: {self._degradation_type}, "
            f"输入形状: {data.shape}, 媒体类型: {self.media_type}"
        )

        # 应用选中的降质处理
        result = self._degrader.process(data)

        logger.info(f"第三阶段降质完成 - 输出形状: {result.shape}")
        return result

    def preprocess(self, data: np.ndarray) -> np.ndarray:
        """第三阶段预处理：根据降质类型做针对性准备"""
        # 示例：对于抖动(shake)降质，先转为float32避免整数溢出
        if self._degradation_type == 'shake' and data.dtype == np.uint8:
            return data.astype(np.float32) / 255.0
        return data

    def postprocess(self, data: np.ndarray) -> np.ndarray:
        """第三阶段后处理：根据降质类型做针对性修正"""
        # 对浮点数据转回uint8
        if np.issubdtype(data.dtype, np.floating):
            return (np.clip(data, 0.0, 1.0) * 255).astype(np.uint8)
        return np.clip(data, 0, 255).astype(np.uint8)

    @property
    def degradation_type(self) -> Optional[str]:
        """获取当前降质类型"""
        return self._degradation_type
