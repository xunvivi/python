import numpy as np
from core.base_degradation import BaseDegradation


class NoiseDegradation(BaseDegradation):
    """
    噪声退化处理类（适用于图像和视频帧）
    支持三种噪声类型：高斯噪声、泊松噪声、椒盐噪声（中文参数直接匹配）
    """
    # 允许的参数列表
    allowed_params = ['noise_type', 'intensity', 'density', 'salt_pepper_ratio']

    def validate_params(self):
        """验证并标准化输入参数，确保参数符合各噪声类型的要求"""
        super().validate_params()  # 调用父类验证方法

        # 1. 验证噪声类型（中文匹配）
        valid_noise_types = ["高斯噪声", "泊松噪声", "椒盐噪声"]
        noise_type = self.params.get('noise_type', '高斯噪声')  # 默认高斯噪声

        # 检查是否为支持的噪声类型
        if noise_type not in valid_noise_types:
            raise ValueError(
                f"不支持的噪声类型: {noise_type}，"
                f"支持的类型为: {valid_noise_types}"
            )
        self.params['noise_type'] = noise_type
        print(f"[噪声配置] 类型: {noise_type}")

        # 2. 验证强度参数（不同噪声类型含义不同）
        if noise_type in ["高斯噪声", "泊松噪声"]:
            # 高斯噪声：intensity = 标准差（0.01-30）
            # 泊松噪声：intensity = 缩放因子（0.01-30）
            intensity = self.params.get('intensity', 5.0)
            validated_intensity = np.clip(intensity, 0.01, 30.0)
            self.params['intensity'] = validated_intensity
            print(f"[噪声配置] 强度: {validated_intensity}")

        elif noise_type == "椒盐噪声":
            # 椒盐噪声：intensity = 噪声幅度（0.01-1.0，控制黑白程度）
            intensity = self.params.get('intensity', 1.0)
            validated_intensity = np.clip(intensity, 0.01, 1.0)
            self.params['intensity'] = validated_intensity
            print(f"[噪声配置] 幅度: {validated_intensity} (0-1，控制噪声明暗程度)")

            # 3. 验证椒盐噪声特有参数：密度（被污染像素比例）
            density_percent = self.params.get('density', 5.0)  # 前端传百分比（如5表示5%）
            density = np.clip(density_percent / 100, 0.01, 0.2)  # 转换为0.01-0.2的比例
            self.params['density'] = density
            print(f"[噪声配置] 密度: {density_percent}% ({density:.2f}比例的像素被污染)")

            # 4. 验证盐/椒比例（盐噪声占总噪声的比例）
            salt_ratio = self.params.get('salt_pepper_ratio', 0.5)
            validated_ratio = np.clip(salt_ratio, 0.1, 0.9)
            self.params['salt_pepper_ratio'] = validated_ratio
            print(f"[噪声配置] 盐/椒比例: {validated_ratio} (盐噪声占比)")

        # 移除非当前噪声类型的无关参数
        if noise_type != "椒盐噪声":
            self.params.pop('density', None)
            self.params.pop('salt_pepper_ratio', None)

    def apply(self, data: np.ndarray) -> np.ndarray:
        """
        向图像/视频帧添加噪声

        参数:
            data: 输入的RGB图像或视频帧，形状为 (H, W, 3)， dtype为uint8

        返回:
            添加噪声后的图像/视频帧，形状和 dtype 与输入一致
        """
        # 确保输入格式正确
        if len(data.shape) != 3 or data.shape[2] != 3:
            raise ValueError(f"输入数据必须是RGB格式的图像 (H, W, 3)，当前形状: {data.shape}")

        noise_type = self.params['noise_type']
        frame = data.astype(np.float32)  # 转为float32以避免计算溢出
        result = None

        if noise_type == "高斯噪声":
            # 高斯噪声：生成均值为0、标准差为intensity的噪声
            sigma = self.params['intensity']
            noise = np.random.normal(loc=0, scale=sigma, size=frame.shape)
            result = frame + noise  # 叠加噪声

        elif noise_type == "泊松噪声":
            # 泊松噪声：与图像亮度相关，亮区域噪声更明显
            scale = self.params['intensity']
            # 归一化图像到[0, scale]范围，生成泊松分布噪声
            normalized_frame = frame / 255.0 * scale
            poisson_samples = np.random.poisson(normalized_frame)  # 泊松采样
            result = poisson_samples / scale * 255.0  # 还原到[0,255]范围

        elif noise_type == "椒盐噪声":
            # 椒盐噪声：随机生成白色（盐）和黑色（椒）噪声点
            density = self.params['density']
            salt_ratio = self.params['salt_pepper_ratio']
            intensity = self.params['intensity']

            # 计算总像素数和噪声像素数
            height, width = frame.shape[:2]
            total_pixels = height * width
            total_noise_pixels = int(total_pixels * density)  # 总噪声像素数

            # 分配盐噪声和椒噪声的数量
            salt_pixels = int(total_noise_pixels * salt_ratio)
            pepper_pixels = total_noise_pixels - salt_pixels

            # 随机生成噪声位置坐标
            # 盐噪声（白色）坐标
            salt_y = np.random.randint(0, height, salt_pixels)
            salt_x = np.random.randint(0, width, salt_pixels)
            # 椒噪声（黑色）坐标
            pepper_y = np.random.randint(0, height, pepper_pixels)
            pepper_x = np.random.randint(0, width, pepper_pixels)

            # 应用噪声（受强度控制明暗程度）
            result = frame.copy()
            result[salt_y, salt_x] = 255 * intensity  # 盐噪声（白色）
            result[pepper_y, pepper_x] = 0 * intensity  # 椒噪声（黑色）

        # 确保像素值在[0, 255]范围内，转回uint8格式
        return np.clip(result, 0, 255).astype(np.uint8)

