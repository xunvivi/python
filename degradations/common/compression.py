import cv2
import numpy as np
import os
import subprocess
import tempfile
from core.base_degradation import BaseDegradation


class CompressionDegradation(BaseDegradation):
    """压缩退化（支持图像和视频，兼容不同OpenCV版本）"""
    allowed_params = ['quality', 'format', 'bitrate', 'fps']

    SUPPORTED_FORMATS = {
        # 图像格式
        'jpeg': {
            'type': 'image',
            'ext': '.jpg',
            'encode_param': cv2.IMWRITE_JPEG_QUALITY,
            'default_quality': 80,
            'bitrate_supported': False
        },
        'png': {
            'type': 'image',
            'ext': '.png',
            'encode_param': cv2.IMWRITE_PNG_COMPRESSION,
            'default_quality': 3,
            'bitrate_supported': False
        },
        'webp': {
            'type': 'image',
            'ext': '.webp',
            'encode_param': cv2.IMWRITE_WEBP_QUALITY,
            'default_quality': 80,
            'bitrate_supported': False
        },
        # 视频格式 - 优先使用浏览器兼容的编解码器
        'h264': {
            'type': 'video',
            'ext': '.mp4',
            'codec': 'H264',  # 浏览器标准编码
            'default_quality': 23,
            'default_bitrate': 2000,
            'bitrate_supported': True
        },
        'mpeg4': {
            'type': 'video',
            'ext': '.mp4',
            'codec': 'mp4v',  # MP4标准编码
            'default_quality': 5,
            'default_bitrate': 1500,
            'bitrate_supported': True
        }
    }

    # 编解码器回退列表 - 优先浏览器兼容编码
    CODEC_FALLBACKS = ['H264', 'mp4v', 'XVID', 'MJPG']

    def validate_params(self):
        super().validate_params()

        # 1. 验证格式
        fmt = self.params.get('format', 'jpeg').lower()
        if fmt not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"不支持的压缩格式: {fmt}，支持的格式: {list(self.SUPPORTED_FORMATS.keys())}"
            )
        self.params['format'] = fmt
        format_info = self.SUPPORTED_FORMATS[fmt]

        # 2. 验证质量参数
        quality = self.params.get('quality', format_info['default_quality'])
        if format_info['type'] == 'image':
            if fmt == 'png':
                quality = max(0, min(9, int(quality)))
            else:
                quality = max(1, min(100, int(quality)))
        else:
            if fmt == 'h264':
                quality = max(0, min(51, int(quality)))
            else:
                quality = max(0, min(31, int(quality)))
        self.params['quality'] = quality

        # 3. 验证比特率参数
        if format_info['bitrate_supported']:
            bitrate = self.params.get('bitrate', format_info['default_bitrate'])
            self.params['bitrate'] = max(100, min(20000, int(bitrate)))
        else:
            self.params.pop('bitrate', None)

        # 4. 验证帧率
        if format_info['type'] == 'video':
            self.params['fps'] = self.params.get('fps', 30)

    def apply(self, data: np.ndarray) -> np.ndarray:
        fmt = self.params['format']
        format_info = self.SUPPORTED_FORMATS[fmt]

        if format_info['type'] == 'image':
            return self._apply_image_compression(data, fmt, format_info)
        else:
            return self._apply_video_compression(data, fmt, format_info)

    def _apply_image_compression(self, data: np.ndarray, fmt: str, format_info: dict) -> np.ndarray:
        if len(data.shape) not in (2, 3):
            raise ValueError(f"图像压缩需要2维或3维输入，实际输入: {data.shape}")

        frame_bgr = cv2.cvtColor(data, cv2.COLOR_RGB2BGR) if len(data.shape) == 3 else data
        encode_param = [format_info['encode_param'], self.params['quality']]

        try:
            _, encoded = cv2.imencode(format_info['ext'], frame_bgr, encode_param)
            if not _:
                raise RuntimeError(f"图像编码失败: {fmt}")
            decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR if len(data.shape) == 3 else cv2.IMREAD_GRAYSCALE)
            return cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB) if len(decoded.shape) == 3 else decoded
        except Exception as e:
            raise RuntimeError(f"图像压缩失败: {str(e)}") from e

    def _try_create_video_writer(self, temp_file, fps, w, h, c):
        """尝试使用不同编解码器创建视频写入器"""
        # 首先尝试默认编解码器
        fmt = self.params['format']
        format_info = self.SUPPORTED_FORMATS[fmt]

        codecs_to_try = [format_info['codec']] + self.CODEC_FALLBACKS

        for codec in codecs_to_try:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                out = cv2.VideoWriter(
                    temp_file,
                    fourcc,
                    fps,
                    (w, h),
                    isColor=(c == 3)
                )

                if out.isOpened():
                    print(f"成功使用编解码器: {codec}")
                    return out, codec
                else:
                    out.release()
            except Exception as e:
                print(f"编解码器 {codec} 失败: {str(e)}")
                continue

        raise RuntimeError(f"所有编解码器都失败了。尝试的编解码器: {codecs_to_try}")

    def _apply_video_compression(self, data: np.ndarray, fmt: str, format_info: dict) -> np.ndarray:
        """使用FFmpeg处理视频压缩，确保浏览器兼容性"""
        # 适配单帧/批量输入
        is_single_frame = False
        original_shape = data.shape
        if len(data.shape) == 3:
            if data.shape[-1] != 3:
                raise ValueError(f"单帧视频需要3通道输入，实际输入: {data.shape}")
            data = np.expand_dims(data, axis=0)
            is_single_frame = True

        if len(data.shape) != 4 or data.shape[-1] != 3:
            raise ValueError(f"视频压缩需要4维输入（[N, H, W, 3]），实际输入: {original_shape}")

        n_frames, h, w, c = data.shape
        fps = self.params['fps']
        quality = self.params['quality']
        bitrate = self.params.get('bitrate', 1000)

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_input:
            temp_input_path = temp_input.name
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
            temp_output_path = temp_output.name

        try:
            # 1. 先用OpenCV创建临时视频文件
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 使用基础编码创建临时文件
            out = cv2.VideoWriter(temp_input_path, fourcc, fps, (w, h), True)

            if not out.isOpened():
                raise RuntimeError("无法创建临时视频文件")

            # 写入所有帧
            for frame in data:
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                out.write(frame_bgr)
            out.release()

            # 2. 使用FFmpeg重新编码为浏览器兼容格式
            self._compress_with_ffmpeg(temp_input_path, temp_output_path, quality, bitrate, fps)

            # 3. 读取FFmpeg处理后的视频
            cap = cv2.VideoCapture(temp_output_path)
            if not cap.isOpened():
                raise RuntimeError(f"无法读取FFmpeg处理后的视频文件")

            # 验证视频属性
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            print(f"FFmpeg压缩后视频信息: {frame_count}帧, {video_fps}fps")

            compressed_frames = []
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                compressed_frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            cap.release()

            if not compressed_frames:
                raise RuntimeError("FFmpeg压缩后的视频没有有效帧")

            # 确保帧数量一致
            if len(compressed_frames) < n_frames:
                compressed_frames.extend([compressed_frames[-1]] * (n_frames - len(compressed_frames)))
            else:
                compressed_frames = compressed_frames[:n_frames]

            # 恢复单帧维度
            result = np.array(compressed_frames)
            if is_single_frame:
                result = np.squeeze(result, axis=0)

            return result

        except Exception as e:
            raise RuntimeError(f"视频压缩失败: {str(e)}") from e
        finally:
            # 清理临时文件
            for temp_file in [temp_input_path, temp_output_path]:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        print(f"临时文件清理失败: {str(e)}")

    def _compress_with_ffmpeg(self, input_path, output_path, quality, bitrate, fps):
        """使用FFmpeg进行视频压缩，确保浏览器兼容性"""
        try:
            # 构建FFmpeg命令 - 针对浏览器优化
            cmd = [
                'ffmpeg', '-y',  # 覆盖输出文件
                '-i', input_path,  # 输入文件
                '-c:v', 'libx264',  # H.264编码器
                '-profile:v', 'baseline',  # 基准档次，最大兼容性
                '-level', '3.1',  # 兼容移动设备
                '-pix_fmt', 'yuv420p',  # 标准像素格式
                '-crf', str(min(max(quality, 18), 28)),  # 质量控制(18-28)
                '-maxrate', f'{bitrate}k',  # 最大比特率
                '-bufsize', f'{bitrate * 2}k',  # 缓冲区大小
                '-movflags', '+faststart',  # 优化网络播放
                '-r', str(fps),  # 帧率
                '-preset', 'medium',  # 编码速度vs质量平衡
                output_path
            ]

            # 执行FFmpeg命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5分钟超时
            )

            print(f"FFmpeg压缩成功: CRF={quality}, 比特率={bitrate}k")

        except subprocess.TimeoutExpired:
            raise RuntimeError("FFmpeg处理超时")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg处理失败: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError("找不到FFmpeg，请确保FFmpeg已正确安装并添加到系统PATH中")