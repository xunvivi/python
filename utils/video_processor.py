import cv2
import numpy as np
import subprocess
import tempfile
import os
from pathlib import Path
import logging
from typing import List, Dict, Tuple, Callable, Optional

logger = logging.getLogger(__name__)


class VideoProcessor:
    """增强的视频处理器，优化兼容性与错误处理"""

    # 支持的输出格式与编解码器配置
    SUPPORTED_FORMATS = {
        'mp4': {
            'codecs': ['libx264', 'mpeg4'],
            'extensions': ['.mp4'],
            'browser_compatible': True
        },
        'avi': {
            'codecs': ['XVID', 'MJPG'],
            'extensions': ['.avi'],
            'browser_compatible': False
        }
    }

    @staticmethod
    def read_video(video_path: str) -> Tuple[List[np.ndarray], Dict]:
        """读取视频文件并转换为RGB格式帧

        Args:
            video_path: 视频文件路径

        Returns:
            tuple: (帧列表(RGB格式), 视频信息字典)

        Raises:
            FileNotFoundError: 视频文件不存在
            ValueError: 无法打开视频或视频格式错误
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件（可能格式不支持）: {video_path}")

            # 获取视频基础信息
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0  # 默认为30fps
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            video_info = {
                "fps": fps,
                "frame_count": frame_count,
                "width": width,
                "height": height,
                "duration": frame_count / fps if fps > 0 else 0,
                "path": video_path
            }

            # 读取并转换帧（BGR→RGB）
            frames = []
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break  # 读取完毕

                # 转换为RGB格式（OpenCV默认BGR）
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)
                frame_idx += 1

            cap.release()

            # 验证帧数量（处理可能的读取不完整）
            if frame_count > 0 and abs(len(frames) - frame_count) > 5:
                logger.warning(f"视频帧读取不完整: 预期 {frame_count} 帧, 实际读取 {len(frames)} 帧")

            logger.info(f"成功读取视频: {len(frames)} 帧, {fps:.1f} FPS, {width}x{height}")
            return frames, video_info

        except Exception as e:
            logger.error(f"读取视频失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def process_video_frames(
            frames: List[np.ndarray],
            processing_func: Callable[[np.ndarray], np.ndarray],
            progress_interval: int = 10
    ) -> List[np.ndarray]:
        """处理视频帧并确保维度一致性

        Args:
            frames: 输入帧列表(RGB格式)
            processing_func: 帧处理函数，接收单帧返回处理后帧
            progress_interval: 进度输出间隔（帧数）

        Returns:
            处理后的帧列表

        Raises:
            ValueError: 帧为空或维度不一致
        """
        if not frames:
            raise ValueError("输入帧列表为空，无法处理")

        try:
            processed_frames = []
            total_frames = len(frames)
            # 获取参考帧尺寸（确保所有帧尺寸一致）
            ref_height, ref_width = frames[0].shape[:2]

            for i, frame in enumerate(frames):
                # 进度输出
                if i % progress_interval == 0:
                    progress = (i + 1) / total_frames * 100
                    logger.info(f"处理进度: {i + 1}/{total_frames} ({progress:.1f}%)")

                # 验证帧尺寸一致性
                current_height, current_width = frame.shape[:2]
                if current_height != ref_height or current_width != ref_width:
                    raise ValueError(
                        f"帧尺寸不一致: 第{i + 1}帧为 {current_width}x{current_height}, "
                        f"预期 {ref_width}x{ref_height}"
                    )

                # 处理帧
                processed_frame = processing_func(frame)

                # 确保输出帧为RGB格式且尺寸一致
                if len(processed_frame.shape) != 3 or processed_frame.shape[2] != 3:
                    raise ValueError(f"处理后帧格式错误: 第{i + 1}帧形状为 {processed_frame.shape}")

                processed_frames.append(processed_frame)

            logger.info(f"帧处理完成: 共处理 {len(processed_frames)} 帧")
            return processed_frames

        except Exception as e:
            logger.error(f"帧处理失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def write_video_opencv_fallback(
            frames: List[np.ndarray],
            output_path: str,
            fps: float = 30.0
    ) -> str:
        """使用OpenCV写入视频（备用方案，自动适配编解码器）"""
        if not frames:
            raise ValueError("无帧数据可写入视频")

        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)

            # 获取帧尺寸（RGB→BGR转换前）
            height, width = frames[0].shape[:2]
            # 尝试不同编解码器组合
            codec_options = [
                ("mp4v", ".mp4"),  # MPEG-4
                ("XVID", ".avi"),  # XVID
                ("MJPG", ".avi"),  # Motion JPEG
                ("avc1", ".mp4")  # H.264 (OpenCV可能不支持)
            ]

            for codec, ext in codec_options:
                # 构建输出路径
                base_name = os.path.splitext(os.path.basename(output_path))[0]
                temp_path = os.path.join(output_dir, f"{base_name}_{codec}{ext}")

                try:
                    fourcc = cv2.VideoWriter_fourcc(*codec)
                    out = cv2.VideoWriter(
                        temp_path,
                        fourcc,
                        fps,
                        (width, height)
                    )

                    if not out.isOpened():
                        logger.warning(f"编解码器 {codec} 无法初始化，跳过")
                        continue

                    # 写入帧（RGB→BGR转换）
                    for frame in frames:
                        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        out.write(frame_bgr)

                    out.release()

                    # 验证文件有效性
                    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 1024:  # 大于1KB
                        logger.info(f"OpenCV写入成功: {temp_path} (编解码器: {codec})")
                        return temp_path

                except Exception as e:
                    logger.warning(f"编解码器 {codec} 处理失败: {str(e)}")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)  # 清理失败文件
                    continue

            raise RuntimeError("所有OpenCV编解码器均尝试失败，无法写入视频")

        except Exception as e:
            logger.error(f"OpenCV视频写入失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def write_video_ffmpeg(
            frames: List[np.ndarray],
            output_path: str,
            fps: float = 30.0,
            crf: int = 23  # 质量控制（0-51，越低质量越高）
    ) -> str:
        """使用FFmpeg写入视频（推荐方案，兼容性更好）"""
        if not frames:
            raise ValueError("无帧数据可写入视频")

        try:
            # 检查FFmpeg是否可用
            try:
                subprocess.run(
                    ["ffmpeg", "-version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
            except (subprocess.SubprocessError, FileNotFoundError):
                raise RuntimeError("未找到FFmpeg，请安装FFmpeg后重试")

            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)

            # 帧信息
            height, width = frames[0].shape[:2]
            total_frames = len(frames)

            # 构建输出路径（确保.mp4格式）
            if not output_path.endswith(".mp4"):
                output_path = os.path.splitext(output_path)[0] + ".mp4"

            # FFmpeg命令（通过管道输入原始帧数据）
            cmd = [
                "ffmpeg",
                "-y",  # 覆盖输出文件
                "-f", "rawvideo",  # 输入格式
                "-vcodec", "rawvideo",  # 输入编码
                "-s", f"{width}x{height}",  # 分辨率
                "-pix_fmt", "rgb24",  # 输入像素格式（RGB）
                "-r", f"{fps:.2f}",  # 帧率
                "-i", "-",  # 从标准输入读取

                # 输出配置（确保浏览器兼容）
                "-c:v", "libx264",  # H.264编码
                "-preset", "medium",  # 编码速度/质量平衡
                "-crf", str(crf),  # 恒定质量模式
                "-pix_fmt", "yuv420p",  # 浏览器兼容的像素格式
                "-profile:v", "main",  # 兼容主流设备
                "-level", "3.1",  # 编码级别
                "-movflags", "+faststart",  # 优化网页加载
                "-an",  # 无音频流（避免错误）
                output_path
            ]

            logger.info(f"启动FFmpeg处理: {output_path} (帧率: {fps:.1f}, 分辨率: {width}x{height})")

            # 启动FFmpeg进程
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False  # 二进制模式
            )

            # 写入帧数据
            try:
                for i, frame in enumerate(frames):
                    # 进度输出
                    if i % 50 == 0:  # 每50帧输出一次
                        progress = (i + 1) / total_frames * 100
                        logger.info(f"FFmpeg写入进度: {i + 1}/{total_frames} ({progress:.1f}%)")

                    # 确保帧格式正确（uint8类型）
                    if frame.dtype != np.uint8:
                        frame = frame.astype(np.uint8)

                    # 写入原始RGB数据
                    process.stdin.write(frame.tobytes())

                # 关闭输入流并等待完成
                process.stdin.close()
                stdout, stderr = process.communicate(timeout=600)  # 10分钟超时

                # 检查返回码
                if process.returncode != 0:
                    error_msg = stderr.decode("utf-8", errors="ignore")
                    raise RuntimeError(f"FFmpeg执行失败: {error_msg[:500]}")  # 截断长错误

                # 验证输出文件
                if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
                    raise RuntimeError("FFmpeg生成的视频文件无效或为空")

                logger.info(f"FFmpeg写入成功: {output_path} (大小: {os.path.getsize(output_path) / 1024 / 1024:.2f}MB)")
                return output_path

            except subprocess.TimeoutExpired:
                process.kill()
                raise RuntimeError("FFmpeg处理超时（>10分钟）")
            except Exception as e:
                process.kill()
                raise RuntimeError(f"FFmpeg写入过程失败: {str(e)}")

        except Exception as e:
            logger.error(f"FFmpeg视频处理失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def write_video(
            frames: List[np.ndarray],
            output_path: str,
            fps: float = 30.0,
            prefer_ffmpeg: bool = True
    ) -> str:
        """写入视频文件（自动选择最佳方案）

        Args:
            frames: 帧列表(RGB格式)
            output_path: 目标输出路径
            fps: 帧率
            prefer_ffmpeg: 是否优先使用FFmpeg

        Returns:
            实际输出文件路径
        """
        if not frames:
            raise ValueError("无帧数据可写入")

        logger.info(f"开始写入视频: {output_path} (帧数量: {len(frames)}, 帧率: {fps:.1f})")

        # 优先尝试FFmpeg
        if prefer_ffmpeg:
            try:
                return VideoProcessor.write_video_ffmpeg(frames, output_path, fps)
            except Exception as e:
                logger.warning(f"FFmpeg方案失败，尝试OpenCV备用方案: {str(e)}")

        # 备用方案：OpenCV
        try:
            opencv_path = VideoProcessor.write_video_opencv_fallback(frames, output_path, fps)

            # 尝试转换为浏览器兼容格式（如果不是mp4）
            if not opencv_path.endswith(".mp4"):
                try:
                    return VideoProcessor.convert_to_browser_compatible(opencv_path, output_path)
                except Exception as e:
                    logger.warning(f"格式转换失败，保留原始文件: {str(e)}")

            return opencv_path

        except Exception as e:
            logger.error(f"所有写入方案失败: {str(e)}", exc_info=True)
            raise RuntimeError("无法写入视频文件")

    @staticmethod
    def verify_video_playable(video_path: str) -> bool:
        """验证视频文件是否可正常播放

        Args:
            video_path: 视频文件路径

        Returns:
            bool: 可播放返回True，否则False
        """
        if not os.path.exists(video_path) or os.path.getsize(video_path) < 1024:
            logger.warning(f"视频文件不存在或无效: {video_path}")
            return False

        try:
            # 使用OpenCV验证
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return False

            # 读取前5帧和最后1帧验证
            frame_check_points = [0, 1, 2, -2, -1]  # 检查点
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            success_count = 0

            for idx in frame_check_points:
                # 计算实际帧索引（处理负索引）
                frame_idx = idx if idx >= 0 else max(0, total_frames + idx)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, _ = cap.read()
                if ret:
                    success_count += 1

            cap.release()

            # 至少成功读取3帧才算有效
            result = success_count >= 3
            logger.info(f"视频验证: {'通过' if result else '失败'} (成功读取 {success_count}/5 帧)")
            return result

        except Exception as e:
            logger.warning(f"视频验证失败: {str(e)}")
            return False

    @staticmethod
    def convert_to_browser_compatible(input_path: str, output_path: str) -> str:
        """将视频转换为浏览器兼容格式（H.264 + AAC）

        Args:
            input_path: 输入视频路径
            output_path: 目标输出路径

        Returns:
            转换后视频路径
        """
        try:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"输入文件不存在: {input_path}")

            # 确保输出为mp4
            if not output_path.endswith(".mp4"):
                output_path = os.path.splitext(output_path)[0] + ".mp4"

            # 避免覆盖输入文件
            if os.path.abspath(input_path) == os.path.abspath(output_path):
                temp_path = f"{output_path}.temp.mp4"
            else:
                temp_path = output_path

            # FFmpeg转换命令
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-y",
                "-c:v", "libx264",  # 视频编码
                "-preset", "medium",
                "-crf", "24",  # 略低于源质量，确保压缩
                "-pix_fmt", "yuv420p",  # 浏览器兼容
                "-profile:v", "main",
                "-level", "3.1",
                "-c:a", "aac",  # 音频编码（无音频则自动忽略）
                "-b:a", "128k",  # 音频比特率
                "-ar", "44100",  # 采样率
                "-ac", "2",  # 声道数
                "-movflags", "+faststart",  # 优化加载
                temp_path
            ]

            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode != 0:
                error_msg = result.stderr[:500]
                raise RuntimeError(f"FFmpeg转换失败: {error_msg}")

            # 替换临时文件
            if temp_path != output_path and os.path.exists(temp_path):
                os.replace(temp_path, output_path)

            logger.info(f"视频转换为浏览器兼容格式: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"格式转换失败: {str(e)}", exc_info=True)
            # 转换失败返回原始路径
            return input_path

    @staticmethod
    def create_test_video(
            output_path: str,
            duration: int = 5,
            fps: float = 30,
            width: int = 640,
            height: int = 480
    ) -> str:
        """创建测试视频用于功能验证

        Args:
            output_path: 输出路径
            duration: 视频时长(秒)
            fps: 帧率
            width: 宽度
            height: 高度

        Returns:
            测试视频路径
        """
        try:
            total_frames = int(duration * fps)
            frames = []

            for i in range(total_frames):
                # 创建渐变帧（RGB）
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                ratio = i / total_frames  # 0~1

                # 颜色渐变（红→绿→蓝）
                frame[:, :, 0] = int(255 * max(0, 1 - 2 * ratio))  # R
                frame[:, :, 1] = int(255 * max(0, 1 - 2 * abs(ratio - 0.5)))  # G
                frame[:, :, 2] = int(255 * max(0, 2 * ratio - 1))  # B

                # 添加文字信息
                text = f"Frame {i + 1}/{total_frames} | {width}x{height} | {fps:.1f} FPS"
                cv2.putText(
                    frame,
                    text,
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 255),  # 白色文字
                    2,
                    cv2.LINE_AA
                )

                frames.append(frame)

            # 写入测试视频
            return VideoProcessor.write_video(frames, output_path, fps)

        except Exception as e:
            logger.error(f"创建测试视频失败: {str(e)}", exc_info=True)
            raise


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_output = "test_video.mp4"

    try:
        print("=== 创建测试视频 ===")
        video_path = VideoProcessor.create_test_video(
            test_output,
            duration=3,
            fps=24,
            width=800,
            height=450
        )

        print("=== 验证视频可读性 ===")
        if VideoProcessor.verify_video_playable(video_path):
            print(f"✅ 视频验证通过: {video_path}")
        else:
            print(f"❌ 视频验证失败: {video_path}")

        print("=== 读取并处理视频 ===")
        frames, info = VideoProcessor.read_video(video_path)
        print(f"读取到 {len(frames)} 帧，分辨率: {info['width']}x{info['height']}")


        # 简单处理：添加灰度滤镜
        def gray_filter(frame):
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)  # 转回RGB保持维度


        processed_frames = VideoProcessor.process_video_frames(frames, gray_filter)

        print("=== 写入处理后的视频 ===")
        processed_path = os.path.splitext(video_path)[0] + "_processed.mp4"
        VideoProcessor.write_video(processed_frames, processed_path, fps=info["fps"])
        print(f"处理后的视频: {processed_path}")

    except Exception as e:
        print(f"测试失败: {e}")