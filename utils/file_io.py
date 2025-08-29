import os
import uuid
import mimetypes
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, List, Dict

# 支持的文件扩展名（复用你原始的配置）
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.mpeg', '.mpg', '.webm'}

# 配置目录（保持你原始的路径结构，添加Path类型兼容）
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FILE_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'file')  # 项目根目录下的file文件夹
PROCESSED_DIR = os.path.join(FILE_ROOT, 'processed')
UPLOAD_DIR = FILE_ROOT

# 为了兼容app.py的Path类型调用，同时保留字符串格式（关键适配）
MEDIA_ROOT = Path(FILE_ROOT)  # 供app.py中Path类型使用
MEDIA_ROOT_STR = FILE_ROOT    # 供字符串格式路径使用

# 确保必要目录存在（复用你原始的创建逻辑）
os.makedirs(FILE_ROOT, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


def save_uploaded_file(file, upload_dir=UPLOAD_DIR):
    """保存上传的文件到指定目录（复用你原始代码，无需修改）"""
    try:
        if not file or not hasattr(file, 'filename') or not file.filename:
            raise ValueError("无效的文件对象或文件名为空")

        os.makedirs(upload_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in IMAGE_EXTENSIONS and file_ext not in VIDEO_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {file_ext}")

        unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)

        return file_path
    except Exception as e:
        print(f"保存文件失败: {str(e)}")
        raise


def generate_output_filename(input_path, degradation_type, output_dir=PROCESSED_DIR):
    """生成处理后的输出文件名（复用你原始代码，无需修改）"""
    try:
        os.makedirs(output_dir, exist_ok=True)

        if not input_path or not os.path.exists(input_path):
            raise ValueError("输入文件路径无效或文件不存在")

        filename = os.path.basename(input_path)
        name, ext = os.path.splitext(filename)

        if not degradation_type or not isinstance(degradation_type, str):
            raise ValueError("处理类型参数无效")

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        output_filename = f"{name}_{degradation_type}_{timestamp}{ext}"
        return os.path.join(output_dir, output_filename)
    except Exception as e:
        print(f"生成输出文件名失败: {str(e)}")
        raise


def validate_media_type(file_path, expected_type=None) -> bool | Tuple[bool, Optional[str]]:
    """验证文件是否为支持的媒体类型（修复路径兼容，支持Path类型）"""
    try:
        # 兼容Path对象和字符串路径
        if isinstance(file_path, Path):
            file_path = str(file_path)
        if not file_path or not isinstance(file_path, str):
            return (False, None) if expected_type is None else False

        # 获取文件扩展名（小写）
        ext = os.path.splitext(file_path)[1].lower()

        if ext in IMAGE_EXTENSIONS:
            media_type = 'image'
        elif ext in VIDEO_EXTENSIONS:
            media_type = 'video'
        else:
            return (False, None) if expected_type is None else False

        if expected_type is not None:
            return media_type == expected_type

        return (True, media_type)
    except Exception as e:
        print(f"验证媒体类型失败: {str(e)}")
        return (False, None) if expected_type is None else False


def get_file_size(file_path) -> Tuple[int, str]:
    """获取文件大小（修复Path类型兼容，统一返回格式）"""
    try:
        # 兼容Path对象和字符串路径
        if isinstance(file_path, Path):
            file_path = str(file_path)
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        size_bytes = os.path.getsize(file_path)
        size_human = format_file_size(size_bytes)

        return size_bytes, size_human
    except FileNotFoundError:
        raise
    except Exception as e:
        print(f"获取文件大小失败: {str(e)}")
        raise


def get_file_list(subdir='') -> Tuple[List[Dict], str, str]:
    """获取指定目录下的文件列表（复用你原始代码，无需修改）"""
    try:
        target_dir = os.path.join(FILE_ROOT, subdir)
        if not os.path.exists(target_dir):
            return [], subdir, ''

        files = []
        for entry in os.scandir(target_dir):
            if entry.is_file():
                file_ext = os.path.splitext(entry.name)[1].lower()
                all_extensions = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
                if file_ext in all_extensions:
                    _, file_type = validate_media_type(entry.name)
                    size = entry.stat().st_size
                    size_human = format_file_size(size)

                    files.append({
                        'name': entry.name,
                        'path': os.path.relpath(entry.path, FILE_ROOT),
                        'size': size,
                        'size_human': size_human,
                        'type': file_type,
                        'modified': datetime.fromtimestamp(entry.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                    })

        files.sort(key=lambda x: x['modified'], reverse=True)
        parent_dir = os.path.dirname(subdir) if subdir else ''

        return files, subdir, parent_dir
    except Exception as e:
        print(f"获取文件列表失败: {str(e)}")
        return [], subdir, ''


def format_file_size(size_bytes) -> str:
    """将字节数转换为人类可读的文件大小格式（复用你原始代码，无需修改）"""
    try:
        if size_bytes == 0:
            return "0 B"

        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    except Exception as e:
        print(f"格式化文件大小失败: {str(e)}")
        return "未知大小"


def delete_file(file_path) -> bool:
    """删除指定文件（复用你原始代码，无需修改）"""
    try:
        if not file_path:
            return False

        full_path = os.path.join(FILE_ROOT, file_path)
        real_file_path = os.path.realpath(full_path)
        real_file_root = os.path.realpath(FILE_ROOT)

        if not real_file_path.startswith(real_file_root):
            print("安全错误：尝试删除FILE_ROOT外的文件")
            return False

        if os.path.exists(full_path) and os.path.isfile(full_path):
            os.remove(full_path)
            return True
        return False
    except Exception as e:
        print(f"删除文件失败: {str(e)}")
        raise


def get_media_info(file_path) -> Optional[Dict]:
    """
    修复：基于ffprobe获取真实媒体信息（替换你原始的模拟数据）
    用于/api/media-info接口，返回完整的宽高、编码、帧率等信息
    注意：这是一个同步函数，不要使用async/await
    """
    try:
        # 兼容Path对象和字符串路径，获取绝对路径
        if isinstance(file_path, Path):
            file_path = str(file_path)
        if not file_path:
            return None

        # 先获取基础信息（复用你原始的基础逻辑）
        full_path = get_media_path(file_path)  # 调用get_media_path确保路径有效
        is_valid, media_type = validate_media_type(full_path)
        if not is_valid:
            return None

        file_size, file_size_human = get_file_size(full_path)
        file_ext = os.path.splitext(full_path)[1].lower()[1:]  # 扩展名（不带点）

        # 初始化媒体信息字典
        media_info = {
            "file_path": os.path.relpath(full_path, FILE_ROOT) if full_path.startswith(FILE_ROOT) else os.path.relpath(
                full_path, os.path.dirname(FILE_ROOT)),  # 相对路径（供前端显示）
            "full_path": full_path,
            "file_size": file_size,
            "file_size_human": file_size_human,
            "media_type": media_type,
            "format": file_ext,
            "created_time": datetime.fromtimestamp(os.path.getctime(full_path)).strftime('%Y-%m-%d %H:%M:%S'),
            "modified_time": datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%Y-%m-%d %H:%M:%S'),
            # 待填充的ffprobe信息
            "width": None, "height": None, "video_codec": None,
            "fps": None, "duration": None, "video_bitrate": None,
            "audio_codec": None, "sample_rate": None, "channels": None,
            "color_space": None, "bit_depth": None, "warning": None
        }

        # 调用ffprobe获取详细信息（核心修复）
        try:
            # 修复：使用更详细的 ffprobe 命令
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_format", "-show_streams",
                    full_path
                ],
                capture_output=True, text=True, check=True, timeout=15
            )

            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, "ffprobe")

            ffprobe_data = json.loads(result.stdout)
            streams = ffprobe_data.get("streams", [])
            format_data = ffprobe_data.get("format", {})

            print(f"DEBUG: ffprobe原始数据 - streams数量: {len(streams)}")
            if streams:
                print(f"DEBUG: 第一个流信息: {streams[0]}")

            # 解析视频/音频流信息
            for stream in streams:
                codec_type = stream.get("codec_type")
                print(f"DEBUG: 处理流类型: {codec_type}")

                if codec_type == "video":
                    # 视频基础信息
                    media_info["width"] = stream.get("width")
                    media_info["height"] = stream.get("height")
                    media_info["video_codec"] = stream.get("codec_long_name") or stream.get("codec_name")
                    media_info["color_space"] = stream.get("pix_fmt")

                    # 帧率（处理分数形式，如29/1 → 29.0）
                    if "r_frame_rate" in stream and stream["r_frame_rate"]:
                        rate_str = str(stream["r_frame_rate"])
                        if "/" in rate_str:
                            try:
                                num, den = rate_str.split("/")
                                num, den = int(num), int(den)
                                if den != 0:
                                    media_info["fps"] = round(num / den, 2)
                            except (ValueError, ZeroDivisionError):
                                pass

                    # 视频比特率
                    if "bit_rate" in stream and stream["bit_rate"]:
                        try:
                            media_info["video_bitrate"] = int(float(stream["bit_rate"]))
                        except (ValueError, TypeError):
                            pass

                    # 位深处理
                    if "bits_per_raw_sample" in stream and stream["bits_per_raw_sample"]:
                        try:
                            media_info["bit_depth"] = int(stream["bits_per_raw_sample"])
                        except (ValueError, TypeError):
                            pass

                    # 如果没有位深信息，尝试从像素格式推断
                    if media_info["bit_depth"] is None and media_info["color_space"]:
                        pix_fmt = media_info["color_space"]
                        depth_map = {
                            'yuv420p': 8, 'nv12': 8, 'yuv422p': 8, 'yuvj420p': 8,
                            'yuv420p10le': 10, 'p010le': 10, 'yuv444p12le': 12,
                            'rgb24': 8, 'rgba': 8, 'bgr24': 8, 'bgra': 8
                        }
                        media_info["bit_depth"] = depth_map.get(pix_fmt)

                elif codec_type == "audio":
                    # 音频信息
                    media_info["audio_codec"] = stream.get("codec_long_name") or stream.get("codec_name")

                    if "sample_rate" in stream and stream["sample_rate"]:
                        try:
                            media_info["sample_rate"] = int(stream["sample_rate"])
                        except (ValueError, TypeError):
                            pass

                    if "channels" in stream and stream["channels"]:
                        try:
                            media_info["channels"] = int(stream["channels"])
                        except (ValueError, TypeError):
                            pass

                    if "bit_rate" in stream and stream["bit_rate"]:
                        try:
                            media_info["audio_bitrate"] = int(float(stream["bit_rate"]))
                        except (ValueError, TypeError):
                            pass

            # 时长处理（优先使用format的duration）
            duration = None
            if format_data.get("duration"):
                try:
                    duration = round(float(format_data["duration"]), 2)
                except (ValueError, TypeError):
                    pass

            # 如果format没有duration，尝试从视频流获取
            if duration is None:
                video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
                if video_stream and video_stream.get("duration"):
                    try:
                        duration = round(float(video_stream["duration"]), 2)
                    except (ValueError, TypeError):
                        pass

            if duration is not None:
                media_info["duration"] = duration

        except subprocess.TimeoutExpired:
            media_info["warning"] = "ffprobe超时，未能获取完整信息"
            print(f"ffprobe超时: {full_path}")
        except Exception as e:
            media_info["warning"] = f"ffprobe解析失败: {str(e)}"
            print(f"ffprobe获取信息失败: {str(e)}")

        return media_info
    except Exception as e:
        print(f"获取媒体信息失败: {str(e)}")
        return None


def get_directory_size(directory_path) -> int:
    """计算目录总大小（复用你原始代码，无需修改）"""
    try:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, IOError):
                    continue
        return total_size
    except Exception as e:
        print(f"计算目录大小失败: {str(e)}")
        return 0


def get_media_path(file_path) -> str:
    """修复Windows系统路径处理，正确解析包含..\的相对路径，支持processed目录访问"""
    try:
        if not file_path:
            raise ValueError("文件路径不能为空")

        # 1. 统一路径分隔符为Windows格式（处理前端可能传入的/）
        file_path = file_path.replace('/', '\\')

        # 2. 解析路径中的..和.，得到标准化路径（关键修复）
        normalized_path = os.path.normpath(file_path)

        # 3. 确定基础目录和完整路径
        full_path = None

        # 3.1 如果路径以 ..\processed\ 开头，特殊处理
        if normalized_path.startswith('..\\processed\\'):
            # 计算项目根目录（FILE_ROOT的父目录）
            project_root = os.path.dirname(FILE_ROOT)
            # 移除开头的 ..\ 并拼接到项目根目录
            relative_path = normalized_path[3:]  # 移除 '..\'
            full_path = os.path.join(project_root, relative_path)
        # 3.2 如果路径以 processed\ 开头（已经是相对于项目根的路径）
        elif normalized_path.startswith('processed\\'):
            project_root = os.path.dirname(FILE_ROOT)
            full_path = os.path.join(project_root, normalized_path)
        # 3.3 普通情况：相对于FILE_ROOT的路径
        else:
            full_path = os.path.join(FILE_ROOT, normalized_path)

        # 4. 转换为绝对路径，确保一致性
        full_path = os.path.abspath(full_path)

        # 5. 获取真实路径（解析符号链接等）
        real_full_path = os.path.realpath(full_path)
        real_file_root = os.path.realpath(FILE_ROOT)

        # 计算processed目录的真实路径
        project_root = os.path.dirname(FILE_ROOT)
        processed_dir = os.path.join(project_root, 'processed')
        real_processed_dir = os.path.realpath(processed_dir)

        # 6. 安全校验：允许访问FILE_ROOT或processed目录
        is_in_file_root = real_full_path.lower().startswith(real_file_root.lower())
        is_in_processed = real_full_path.lower().startswith(real_processed_dir.lower())

        if not (is_in_file_root or is_in_processed):
            raise ValueError(f"不允许访问FILE_ROOT和processed目录外的文件: {file_path}")

        # 7. 验证文件存在性和类型（保持不变）
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"路径不是文件: {file_path}")
        if not validate_media_type(full_path)[0]:
            raise FileNotFoundError(f"文件不是有效的媒体文件: {file_path}")

        return full_path
    except (FileNotFoundError, ValueError):
        raise
    except Exception as e:
        print(f"获取媒体路径失败: {str(e)}")
        raise FileNotFoundError(f"获取媒体路径失败: {str(e)}")


def get_file_url(file_path, base_url="/static/files") -> Optional[str]:
    """获取文件的URL路径"""
    try:
        if not file_path:
            return None

        url_path = file_path.replace(os.path.sep, '/')
        return f"{base_url.rstrip('/')}/{url_path.lstrip('/')}"
    except Exception as e:
        print(f"生成文件URL失败: {str(e)}")
        return None


def create_directory(dir_path) -> bool:
    """创建目录（复用你原始代码，无需修改）"""
    try:
        if not dir_path:
            return False

        full_path = os.path.join(FILE_ROOT, dir_path)
        real_dir_path = os.path.realpath(full_path)
        real_file_root = os.path.realpath(FILE_ROOT)

        if not real_dir_path.startswith(real_file_root):
            print("安全错误：尝试在FILE_ROOT外创建目录")
            return False

        os.makedirs(full_path, exist_ok=True)
        return True
    except Exception as e:
        print(f"创建目录失败: {str(e)}")
        return False


def move_file(src_path, dest_path) -> bool:
    """移动文件（复用你原始代码，无需修改）"""
    try:
        if not src_path or not dest_path:
            return False

        src_full_path = os.path.join(FILE_ROOT, src_path)
        dest_full_path = os.path.join(FILE_ROOT, dest_path)
        real_src_path = os.path.realpath(src_full_path)
        real_dest_path = os.path.realpath(dest_full_path)
        real_file_root = os.path.realpath(FILE_ROOT)

        if not (real_src_path.startswith(real_file_root) and real_dest_path.startswith(real_file_root)):
            print("安全错误：尝试在FILE_ROOT外移动文件")
            return False

        if not os.path.exists(src_full_path):
            return False

        dest_dir = os.path.dirname(dest_full_path)
        os.makedirs(dest_dir, exist_ok=True)

        os.rename(src_full_path, dest_full_path)
        return True
    except Exception as e:
        print(f"移动文件失败: {str(e)}")
        return False


def copy_file(src_path, dest_path) -> bool:
    """复制文件（复用你原始代码，无需修改）"""
    try:
        import shutil

        if not src_path or not dest_path:
            return False

        src_full_path = os.path.join(FILE_ROOT, src_path)
        dest_full_path = os.path.join(FILE_ROOT, dest_path)
        real_src_path = os.path.realpath(src_full_path)
        real_dest_path = os.path.realpath(dest_full_path)
        real_file_root = os.path.realpath(FILE_ROOT)

        if not (real_src_path.startswith(real_file_root) and real_dest_path.startswith(real_file_root)):
            print("安全错误：尝试在FILE_ROOT外复制文件")
            return False

        if not os.path.exists(src_full_path):
            return False

        dest_dir = os.path.dirname(dest_full_path)
        os.makedirs(dest_dir, exist_ok=True)

        shutil.copy2(src_full_path, dest_full_path)
        return True
    except Exception as e:
        print(f"复制文件失败: {str(e)}")
        return False


def cleanup_old_files(directory_path, days_old=30) -> Tuple[int, int]:
    """清理指定天数前的旧文件（复用你原始代码，无需修改）"""
    try:
        import time

        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        deleted_count = 0
        freed_space = 0

        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if os.path.getmtime(file_path) < cutoff_time:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_count += 1
                        freed_space += file_size
                except (OSError, IOError) as e:
                    print(f"删除文件失败 {file_path}: {str(e)}")
                    continue

        return deleted_count, freed_space
    except Exception as e:
        print(f"清理旧文件失败: {str(e)}")
        return 0, 0

