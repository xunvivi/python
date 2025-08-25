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


class Stage2Degradation(BaseDegradation):
    """
    第二阶段降质处理类：在第一阶段基础上增强降质效果

    保持与第一阶段相同的处理顺序（模糊→重采样→噪声→压缩），
    但使用更强的降质参数，实现媒体质量的进一步恶化
    """
    # 允许的参数列表，与第一阶段保持一致以便前端统一处理
    allowed_params = [
        'blur',  # 模糊参数（比第一阶段更强）
        'resample',  # 重采样参数（比第一阶段更低分辨率）
        'noise',  # 噪声参数（比第一阶段更强）
        'compression'  # 压缩参数（比第一阶段压缩率更高）
    ]

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化第二阶段降质处理器

        Args:
            params: 包含各子降质参数的字典，格式与第一阶段相同但强度更高
                {
                    "blur": {...},      # 模糊参数（建议比第一阶段大20-50%）
                    "resample": {...},  # 重采样参数（建议比第一阶段分辨率低20-40%）
                    "noise": {...},     # 噪声参数（建议比第一阶段强30-60%）
                    "compression": {...}# 压缩参数（建议比第一阶段质量低20-40%）
                }
        """
        super().__init__(params)

        # 初始化子降质处理器（延迟初始化）
        self._blur = None
        self._resample = None
        self._noise = None
        self._compression = None

    def validate_params(self) -> None:
        """验证第二阶段降质参数的合法性"""
        # 检查模糊参数，第二阶段需要比基础值更大
        if 'blur' in self.params:
            if not isinstance(self.params['blur'], dict):
                raise ValueError("'blur' 参数必须是字典类型")
            # 示例：检查核大小是否为奇数（模糊处理通常需要）
            if 'kernel_size' in self.params['blur']:
                if self.params['blur']['kernel_size'] % 2 == 0:
                    raise ValueError("'blur.kernel_size' 必须是奇数")

        # 检查重采样参数，确保分辨率低于第一阶段
        if 'resample' in self.params:
            if not isinstance(self.params['resample'], dict):
                raise ValueError("'resample' 参数必须是字典类型")
            # 检查分辨率是否合法
            if 'width' in self.params['resample'] and self.params['resample']['width'] < 160:
                raise ValueError("'resample.width' 不能小于160像素（避免过度降质）")
            if 'height' in self.params['resample'] and self.params['resample']['height'] < 90:
                raise ValueError("'resample.height' 不能小于90像素（避免过度降质）")

        # 检查噪声参数
        if 'noise' in self.params:
            if not isinstance(self.params['noise'], dict):
                raise ValueError("'noise' 参数必须是字典类型")
            # 检查噪声类型是否支持
            if 'type' in self.params['noise'] and self.params['noise']['type'] not in ['gaussian', 'salt_pepper',
                                                                                       'poisson']:
                raise ValueError("'noise.type' 必须是 'gaussian', 'salt_pepper' 或 'poisson'")

        # 检查压缩参数
        if 'compression' in self.params:
            if not isinstance(self.params['compression'], dict):
                raise ValueError("'compression' 参数必须是字典类型")
            # 检查压缩质量是否在合理范围
            if 'quality' in self.params['compression']:
                if not (10 <= self.params['compression']['quality'] <= 70):
                    raise ValueError("'compression.quality' 必须在10-70之间（第二阶段建议范围）")

    def _init_degradations(self) -> None:
        """初始化所有子降质处理器，设置更强的默认参数"""
        # 初始化模糊处理器（默认参数比第一阶段强）
        default_blur_params = {'kernel_size': 7, 'sigma': 1.8}
        blur_params = {**default_blur_params, **self.params.get('blur', {})}
        self._blur = BlurDegradation(blur_params)
        self._blur.media_type = self.media_type

        # 初始化重采样处理器（默认分辨率比第一阶段低）
        default_resample_params = {'width': 480, 'height': 270}
        resample_params = {**default_resample_params, **self.params.get('resample', {})}
        self._resample = ResampleDegradation(resample_params)
        self._resample.media_type = self.media_type

        # 初始化噪声处理器（默认噪声比第一阶段强）
        default_noise_params = {'type': 'gaussian', 'mean': 0, 'var': 0.003}
        noise_params = {**default_noise_params, **self.params.get('noise', {})}
        self._noise = NoiseDegradation(noise_params)
        self._noise.media_type = self.media_type

        # 初始化压缩处理器（默认压缩率比第一阶段高）
        default_compression_params = {'quality': 30}
        compression_params = {**default_compression_params, **self.params.get('compression', {})}
        self._compression = CompressionDegradation(compression_params)
        self._compression.media_type = self.media_type

    def apply(self, data: np.ndarray) -> np.ndarray:
        """
        应用第二阶段降质处理：增强版模糊→更低分辨率重采样→更强噪声→更高压缩率

        Args:
            data: 输入媒体数据（第一阶段处理后的输出）

        Returns:
            经过第二阶段降质处理后的媒体数据
        """
        if self._blur is None:
            self._init_degradations()

        # 记录输入数据信息
        logger.info(
            f"第二阶段降质开始 - 输入数据: 类型={self.media_type}, "
            f"形状={data.shape}, 数据类型={data.dtype}"
        )

        # 1. 应用更强的模糊处理
        blurred_data = self._blur.process(data)
        logger.debug(f"第二阶段模糊处理完成 - 输出形状: {blurred_data.shape}")

        # 2. 应用更低分辨率的重采样
        resampled_data = self._resample.process(blurred_data)
        logger.debug(f"第二阶段重采样处理完成 - 输出形状: {resampled_data.shape}")

        # 3. 应用更强的噪声
        noisy_data = self._noise.process(resampled_data)
        logger.debug(f"第二阶段噪声处理完成 - 输出形状: {noisy_data.shape}")

        # 4. 应用更高压缩率的压缩
        compressed_data = self._compression.process(noisy_data)
        logger.debug(f"第二阶段压缩处理完成 - 输出形状: {compressed_data.shape}")

        logger.info("第二阶段降质处理完成")
        return compressed_data

    def preprocess(self, data: np.ndarray) -> np.ndarray:
        """第二阶段全局预处理"""
        # 第一阶段可能已转为float32，这里做边缘增强以保留更多细节（对抗过度模糊）
        if np.issubdtype(data.dtype, np.floating):
            return self._edge_enhancement(data)
        return data

    def _edge_enhancement(self, data: np.ndarray) -> np.ndarray:
        """边缘增强预处理（可选），用于在强降质下保留更多细节"""
        from scipy.ndimage import gaussian_filter

        # 仅对图像/视频帧应用边缘增强
        if len(data.shape) == 3:  # 单张图像
            blurred = gaussian_filter(data, sigma=1)
            return np.clip(data * 1.1 - blurred * 0.1, 0.0, 1.0)
        elif len(data.shape) == 4:  # 视频帧序列
            result = []
            for frame in data:
                blurred = gaussian_filter(frame, sigma=1)
                enhanced = np.clip(frame * 1.1 - blurred * 0.1, 0.0, 1.0)
                result.append(enhanced)
            return np.array(result)
        return data

    def postprocess(self, data: np.ndarray) -> np.ndarray:
        """第二阶段全局后处理"""
        # 第二阶段降质更强，增加对比度补偿
        if np.issubdtype(data.dtype, np.floating):
            # 对比度增强（简单线性拉伸）
            min_val = data.min()
            max_val = data.max()
            if max_val > min_val:  # 避免除零
                data = (data - min_val) / (max_val - min_val)
            return (data * 255).astype(np.uint8)
        return np.clip(data, 0, 255).astype(np.uint8)
