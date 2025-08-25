import numpy as np
import logging
from typing import Dict, Any, Optional
from core.base_degradation import BaseDegradation
from degradations.blur import BlurDegradation
from degradations.resample import ResampleDegradation
from degradations.noise import NoiseDegradation
from degradations.compression import CompressionDegradation

# 配置日志
logger = logging.getLogger(__name__)


class Stage1Degradation(BaseDegradation):
    """
    第一阶段降质处理类：按顺序应用模糊→重采样→噪声→压缩

    该类继承自BaseDegradation，实现了第一阶段必须包含的四种降质组合
    """
    # 允许的参数列表：每个子降质的参数以字典形式传入
    allowed_params = [
        'blur',  # 模糊参数
        'resample',  # 重采样参数
        'noise',  # 噪声参数
        'compression'  # 压缩参数
    ]

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化第一阶段降质处理器

        Args:
            params: 包含各子降质参数的字典，格式如下：
                {
                    "blur": {...},      # 模糊参数，对应BlurDegradation所需参数
                    "resample": {...},  # 重采样参数，对应ResampleDegradation所需参数
                    "noise": {...},     # 噪声参数，对应NoiseDegradation所需参数
                    "compression": {...}# 压缩参数，对应CompressionDegradation所需参数
                }
        """
        super().__init__(params)

        # 初始化子降质处理器（延迟初始化，在apply时创建）
        self._blur = None
        self._resample = None
        self._noise = None
        self._compression = None

    def validate_params(self) -> None:
        """
        验证第一阶段降质参数的合法性

        检查各子降质参数是否符合要求，若未提供则使用默认值
        """
        # 检查模糊参数
        if 'blur' in self.params:
            if not isinstance(self.params['blur'], dict):
                raise ValueError("'blur' 参数必须是字典类型")

        # 检查重采样参数
        if 'resample' in self.params:
            if not isinstance(self.params['resample'], dict):
                raise ValueError("'resample' 参数必须是字典类型")

        # 检查噪声参数
        if 'noise' in self.params:
            if not isinstance(self.params['noise'], dict):
                raise ValueError("'noise' 参数必须是字典类型")

        # 检查压缩参数
        if 'compression' in self.params:
            if not isinstance(self.params['compression'], dict):
                raise ValueError("'compression' 参数必须是字典类型")

    def _init_degradations(self) -> None:
        """初始化所有子降质处理器（延迟初始化，避免未使用时的资源浪费）"""
        # 初始化模糊处理器
        self._blur = BlurDegradation(self.params.get('blur', {}))
        self._blur.media_type = self.media_type  # 传递媒体类型

        # 初始化重采样处理器
        self._resample = ResampleDegradation(self.params.get('resample', {}))
        self._resample.media_type = self.media_type

        # 初始化噪声处理器
        self._noise = NoiseDegradation(self.params.get('noise', {}))
        self._noise.media_type = self.media_type

        # 初始化压缩处理器
        self._compression = CompressionDegradation(self.params.get('compression', {}))
        self._compression.media_type = self.media_type

    def apply(self, data: np.ndarray) -> np.ndarray:
        """
        应用第一阶段降质处理：模糊→重采样→噪声→压缩

        Args:
            data: 输入媒体数据（图像为3D数组 [H, W, C]，视频为4D数组 [F, H, W, C]）

        Returns:
            经过四步降质处理后的媒体数据
        """
        # 确保子降质处理器已初始化
        if self._blur is None:
            self._init_degradations()

        # 记录输入数据信息
        logger.info(
            f"第一阶段降质开始 - 输入数据: 类型={self.media_type}, "
            f"形状={data.shape}, 数据类型={data.dtype}"
        )

        # 1. 应用模糊处理
        blurred_data = self._blur.process(data)
        logger.debug(f"模糊处理完成 - 输出形状: {blurred_data.shape}")

        # 2. 应用重采样处理（下采样）
        resampled_data = self._resample.process(blurred_data)
        logger.debug(f"重采样处理完成 - 输出形状: {resampled_data.shape}")

        # 3. 应用噪声处理
        noisy_data = self._noise.process(resampled_data)
        logger.debug(f"噪声处理完成 - 输出形状: {noisy_data.shape}")

        # 4. 应用压缩处理
        compressed_data = self._compression.process(noisy_data)
        logger.debug(f"压缩处理完成 - 输出形状: {compressed_data.shape}")

        logger.info("第一阶段降质处理完成")
        return compressed_data

    def preprocess(self, data: np.ndarray) -> np.ndarray:
        """
        第一阶段全局预处理（可选）

        对输入数据进行统一预处理，再传递给各子降质步骤

        Args:
            data: 输入媒体数据

        Returns:
            预处理后的媒体数据
        """
        # 示例：将数据转换为float32类型，便于后续处理
        if data.dtype == np.uint8:
            return data.astype(np.float32) / 255.0
        return data

    def postprocess(self, data: np.ndarray) -> np.ndarray:
        """
        第一阶段全局后处理（可选）

        对所有子降质处理后的结果进行统一后处理

        Args:
            data: 经过所有子降质处理的数据

        Returns:
            后处理后的媒体数据
        """
        # 示例：将数据转换回uint8类型（0-255范围）
        if np.issubdtype(data.dtype, np.floating):
            return (np.clip(data, 0.0, 1.0) * 255).astype(np.uint8)
        return np.clip(data, 0, 255).astype(np.uint8)
