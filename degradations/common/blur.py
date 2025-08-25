import cv2
import numpy as np
from core.base_degradation import BaseDegradation


class BlurDegradation(BaseDegradation):
    """模糊退化（支持高斯模糊和均值模糊）"""
    allowed_params = ['blur_type', 'kernel_size', 'sigma']  # 允许的参数

    def validate_params(self):
        # 设置默认模糊类型
        if 'blur_type' not in self.params:
            self.params['blur_type'] = '高斯模糊'
            print(f"未指定模糊类型，默认使用: {self.params['blur_type']}")
        else:
            print(f"指定的模糊类型: {self.params['blur_type']}")

        # 确保核大小为奇数且为正数
        if 'kernel_size' in self.params:
            original_ks = self.params['kernel_size']
            ks = max(1, original_ks)  # 确保为正数
            ks = ks if ks % 2 == 1 else ks + 1
            self.params['kernel_size'] = ks
            if original_ks != ks:
                print(f"核大小调整: 从 {original_ks} 调整为 {ks} (确保为正奇数)")
            else:
                print(f"使用的核大小: {ks}x{ks}")
        else:
            self.params['kernel_size'] = 5  # 默认核大小
            print(f"未指定核大小，默认使用: {self.params['kernel_size']}x{self.params['kernel_size']}")

        # 确保sigma为正数（仅用于高斯模糊）
        if self.params['blur_type'] == '高斯模糊':
            original_sigma = self.params.get('sigma', 1.0)
            self.params['sigma'] = max(0.1, original_sigma)
            if original_sigma != self.params['sigma']:
                print(f"标准差调整: 从 {original_sigma} 调整为 {self.params['sigma']} (确保为正数)")
            else:
                print(f"使用的标准差(sigma): {self.params['sigma']}")

    def apply(self, data: np.ndarray) -> np.ndarray:
        blur_type = self.params['blur_type']
        kernel_size = self.params['kernel_size']
        print("\n开始进行模糊处理...")

        try:
            if blur_type == '高斯模糊':
                print(f"正在应用{blur_type}，核大小: {kernel_size}x{kernel_size}，标准差: {self.params['sigma']}")
                result = cv2.GaussianBlur(
                    data,
                    (kernel_size, kernel_size),
                    self.params['sigma']
                )
            elif blur_type == '均值模糊':
                print(f"正在应用{blur_type}，核大小: {kernel_size}x{kernel_size}")
                result = cv2.blur(
                    data,
                    (kernel_size, kernel_size)
                )
            else:
                # 默认使用高斯模糊
                sigma = self.params.get('sigma', 1.0)
                print(
                    f"模糊类型'{blur_type}'不支持，默认使用高斯模糊，核大小: {kernel_size}x{kernel_size}，标准差: {sigma}")
                result = cv2.GaussianBlur(
                    data,
                    (kernel_size, kernel_size),
                    sigma
                )
            print("模糊处理完成！")
            return result
        except Exception as e:
            print(f"处理过程中发生错误: {str(e)}")
            raise  # 重新抛出异常，让调用者处理
