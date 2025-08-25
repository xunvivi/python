import numpy as np
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaseDegradation(ABC):
    """
    所有降质处理类的基类，定义了统一的接口和通用功能

    子类必须实现:
    - validate_params(): 验证参数合法性
    - apply(): 应用降质处理
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化降质处理器

        Args:
            params: 降质处理参数，字典类型
        """
        self.params = params or {}  # 参数默认为空字典
        self._media_type = None  # 媒体类型：image 或 video
        self._validate_and_set_params()  # 验证并设置参数

    def _validate_and_set_params(self) -> None:
        """验证并设置参数的总入口"""
        try:
            # 先执行通用参数验证
            self._common_param_validation()
            # 再执行子类的特定参数验证
            self.validate_params()
            logger.info(f"参数验证通过: {self.__class__.__name__}")
        except Exception as e:
            logger.error(f"参数验证失败: {str(e)}")
            raise  # 重新抛出异常，让调用者处理

    def _common_param_validation(self) -> None:
        """通用参数验证逻辑（所有降质处理都需要的验证）"""
        # 检查参数是否为字典类型
        if not isinstance(self.params, dict):
            raise TypeError(f"参数必须是字典类型，实际为: {type(self.params)}")

        # 检查是否包含不支持的参数（如果有定义允许的参数列表）
        if hasattr(self, 'allowed_params'):
            for param in self.params:
                if param not in self.allowed_params:
                    raise ValueError(
                        f"不支持的参数: {param}，允许的参数为: {self.allowed_params}"
                    )

    @property
    def media_type(self) -> Optional[str]:
        """获取媒体类型"""
        return self._media_type

    @media_type.setter
    def media_type(self, value: str) -> None:
        """设置媒体类型并验证"""
        if value not in ['image', 'video']:
            raise ValueError(f"媒体类型必须是 'image' 或 'video'，实际为: {value}")
        self._media_type = value
        logger.info(f"设置媒体类型: {value}")

    @abstractmethod
    def validate_params(self) -> None:
        """
        验证降质处理的特定参数

        子类必须实现此方法，用于验证该降质处理特有的参数
        """
        pass

    @abstractmethod
    def apply(self, data: np.ndarray) -> np.ndarray:
        """
        应用降质处理

        子类必须实现此方法，用于实际执行降质处理

        Args:
            data: 输入的媒体数据（图像或视频帧，numpy数组）

        Returns:
            处理后的媒体数据（numpy数组）
        """
        pass

    def preprocess(self, data: np.ndarray) -> np.ndarray:
        """
        预处理数据（可选）

        可以在子类中重写，用于在降质处理前对数据进行预处理

        Args:
            data: 输入的媒体数据

        Returns:
            预处理后的媒体数据
        """
        # 默认不做预处理，直接返回原始数据
        return data

    def postprocess(self, data: np.ndarray) -> np.ndarray:
        """
        后处理数据（可选）

        可以在子类中重写，用于在降质处理后对数据进行后处理

        Args:
            data: 降质处理后的媒体数据

        Returns:
            后处理后的媒体数据
        """
        # 默认将数据裁剪到有效范围 [0, 255] 并转换为uint8类型
        data = np.clip(data, 0, 255)
        return data.astype(np.uint8)

    def process(self, data: np.ndarray) -> np.ndarray:
        """
        完整的处理流程：预处理 -> 降质处理 -> 后处理

        Args:
            data: 输入的媒体数据

        Returns:
            处理后的媒体数据
        """
        try:
            # 验证输入数据
            self._validate_input_data(data)

            # 完整处理流程
            preprocessed = self.preprocess(data)
            degraded = self.apply(preprocessed)
            result = self.postprocess(degraded)

            logger.info(f"处理完成: {self.__class__.__name__}")
            return result
        except Exception as e:
            logger.error(f"处理失败: {str(e)}")
            raise

    def _validate_input_data(self, data: np.ndarray) -> None:
        """验证输入数据的合法性"""
        if not isinstance(data, np.ndarray):
            raise TypeError(f"输入数据必须是numpy数组，实际为: {type(data)}")

        if len(data.shape) not in [3, 4]:
            raise ValueError(
                f"输入数据维度必须是3（图像）或4（视频帧序列），实际为: {len(data.shape)}"
            )

        # 检查数据类型
        if data.dtype not in [np.uint8, np.float32, np.float64]:
            raise TypeError(
                f"输入数据类型必须是uint8、float32或float64，实际为: {data.dtype}"
            )
