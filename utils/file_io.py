import os
import uuid
import mimetypes
from datetime import datetime
from pathlib import Path

# 支持的文件扩展名（在函数定义前先定义）
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.mpeg', '.mpg', '.webm'}

# 配置目录
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FILE_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'file')  # 项目根目录下的file文件夹
PROCESSED_DIR = os.path.join(FILE_ROOT, 'processed')
UPLOAD_DIR = FILE_ROOT

# 为了兼容app.py，添加MEDIA_ROOT别名
MEDIA_ROOT = Path(FILE_ROOT)

# 确保必要目录存在
os.makedirs(FILE_ROOT, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


def save_uploaded_file(file, upload_dir=UPLOAD_DIR):
    """
    保存上传的文件到指定目录

    Args:
        file: 上传的文件对象（Flask FileStorage对象）
        upload_dir: 上传目录路径，默认为UPLOAD_DIR

    Returns:
        str: 保存的文件完整路径

    Raises:
        Exception: 保存文件失败时抛出异常
    """
    try:
        # 检查文件对象是否有效
        if not file or not hasattr(file, 'filename') or not file.filename:
            raise ValueError("无效的文件对象或文件名为空")

        # 确保上传目录存在
        os.makedirs(upload_dir, exist_ok=True)

        # 生成唯一文件名，避免冲突
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        file_ext = os.path.splitext(file.filename)[1].lower()

        # 验证文件扩展名
        if file_ext not in IMAGE_EXTENSIONS and file_ext not in VIDEO_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {file_ext}")

        unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}{file_ext}"

        # 保存文件
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)  # 适用于Flask的FileStorage对象

        return file_path
    except Exception as e:
        print(f"保存文件失败: {str(e)}")
        raise


def generate_output_filename(input_path, degradation_type, output_dir=PROCESSED_DIR):
    """
    生成处理后的输出文件名

    Args:
        input_path: 输入文件路径
        degradation_type: 处理类型标识
        output_dir: 输出目录路径，默认为PROCESSED_DIR

    Returns:
        str: 输出文件的完整路径

    Raises:
        Exception: 生成文件名失败时抛出异常
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 检查输入路径是否有效
        if not input_path or not os.path.exists(input_path):
            raise ValueError("输入文件路径无效或文件不存在")

        filename = os.path.basename(input_path)
        name, ext = os.path.splitext(filename)

        # 验证处理类型参数
        if not degradation_type or not isinstance(degradation_type, str):
            raise ValueError("处理类型参数无效")

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        output_filename = f"{name}_{degradation_type}_{timestamp}{ext}"
        return os.path.join(output_dir, output_filename)
    except Exception as e:
        print(f"生成输出文件名失败: {str(e)}")
        raise


def validate_media_type(file_path, expected_type=None):
    """
    验证文件是否为支持的媒体类型（图片或视频）

    Args:
        file_path: 文件路径
        expected_type: 期望的媒体类型 ('image', 'video') 或 None

    Returns:
        如果提供了 expected_type:
            bool: 文件是否为期望的媒体类型
        如果没有提供 expected_type:
            tuple: (是否有效, 媒体类型)
                   - 是否有效: bool
                   - 媒体类型: 'image', 'video' 或 None
    """
    try:
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

        # 如果指定了期望类型，则返回是否匹配
        if expected_type is not None:
            return media_type == expected_type

        # 否则返回元组
        return (True, media_type)

    except Exception as e:
        print(f"验证媒体类型失败: {str(e)}")
        return (False, None) if expected_type is None else False


def get_file_size(file_path):
    """
    获取文件大小（字节和人类可读格式）

    Args:
        file_path: 文件路径

    Returns:
        tuple: (字节大小, 人类可读格式)

    Raises:
        FileNotFoundError: 文件不存在
        Exception: 其他错误
    """
    try:
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


def get_file_list(subdir=''):
    """
    获取指定目录下的文件列表

    Args:
        subdir: 子目录路径，相对于FILE_ROOT

    Returns:
        tuple: (文件列表, 当前目录, 父目录)
               - 文件列表: list，包含文件信息的字典列表
               - 当前目录: str
               - 父目录: str
    """
    try:
        target_dir = os.path.join(FILE_ROOT, subdir)
        if not os.path.exists(target_dir):
            return [], subdir, ''

        files = []
        for entry in os.scandir(target_dir):
            if entry.is_file():
                # 获取文件类型
                file_ext = os.path.splitext(entry.name)[1].lower()

                # 使用已定义的扩展名集合
                all_extensions = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
                if file_ext in all_extensions:
                    # 判断是图片还是视频
                    _, file_type = validate_media_type(entry.name)

                    # 获取文件大小（人类可读格式）
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

        # 按修改时间降序排序
        files.sort(key=lambda x: x['modified'], reverse=True)

        # 获取父目录
        parent_dir = os.path.dirname(subdir) if subdir else ''

        return files, subdir, parent_dir
    except Exception as e:
        print(f"获取文件列表失败: {str(e)}")
        return [], subdir, ''


def format_file_size(size_bytes):
    """
    将字节数转换为人类可读的文件大小格式

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        str: 格式化后的文件大小字符串
    """
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


def delete_file(file_path):
    """
    删除指定文件

    Args:
        file_path: 相对于FILE_ROOT的文件路径

    Returns:
        bool: 删除成功返回True，失败返回False

    Raises:
        Exception: 删除文件时发生严重错误
    """
    try:
        if not file_path:
            return False

        full_path = os.path.join(FILE_ROOT, file_path)

        # 安全检查：确保路径在FILE_ROOT内
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


def get_media_info(file_path):
    """
    获取媒体文件的基本信息

    Args:
        file_path: 相对于FILE_ROOT的文件路径

    Returns:
        dict: 包含媒体信息的字典，失败时返回None
    """
    try:
        if not file_path:
            return None

        full_path = os.path.join(FILE_ROOT, file_path)
        if not os.path.exists(full_path):
            return None

        # 验证媒体类型
        is_valid, media_type = validate_media_type(full_path)
        if not is_valid:
            return None

        # 获取文件大小
        file_size = os.path.getsize(full_path)

        # 基础信息
        info = {
            'path': file_path,
            'full_path': full_path,
            'file_size': file_size,
            'file_size_human': format_file_size(file_size),
            'media_type': media_type,
            'format': os.path.splitext(full_path)[1].lower()[1:],  # 扩展名（不带点）
            'created_time': datetime.fromtimestamp(os.path.getctime(full_path)).strftime('%Y-%m-%d %H:%M:%S'),
            'modified_time': datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%Y-%m-%d %H:%M:%S')
        }

        # 尝试获取更多媒体信息
        # 注意：这里是模拟数据，实际项目中需要使用PIL（图片）或ffprobe（视频）
        try:
            if media_type == 'image':
                # 实际项目中应使用PIL获取真实图片信息
                # from PIL import Image
                # with Image.open(full_path) as img:
                #     info.update({
                #         'width': img.width,
                #         'height': img.height,
                #         'mode': img.mode
                #     })
                info.update({
                    'width': 1920,  # 模拟数据
                    'height': 1080,
                    'color_space': 'RGB',
                    'bit_depth': 24
                })
            elif media_type == 'video':
                # 实际项目中应使用ffprobe获取真实视频信息
                # import subprocess
                # result = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', full_path], capture_output=True, text=True)
                info.update({
                    'width': 1920,  # 模拟数据
                    'height': 1080,
                    'duration': 10.5,
                    'fps': 30.0,
                    'video_codec': 'H.264',
                    'audio_codec': 'AAC',
                    'bitrate': 5000000  # 5 Mbps
                })
        except Exception as e:
            print(f"获取详细媒体信息失败: {str(e)}")
            # 获取详细信息失败时保留基础信息

        return info
    except Exception as e:
        print(f"获取媒体信息失败: {str(e)}")
        return None


def get_directory_size(directory_path):
    """
    计算目录总大小

    Args:
        directory_path: 目录路径

    Returns:
        int: 目录大小（字节）
    """
    try:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, IOError):
                    # 跳过无法访问的文件
                    continue
        return total_size
    except Exception as e:
        print(f"计算目录大小失败: {str(e)}")
        return 0


def get_media_path(file_path):
    """
    获取媒体文件的完整路径

    Args:
        file_path: 相对于FILE_ROOT的文件路径

    Returns:
        str: 文件的完整路径

    Raises:
        FileNotFoundError: 文件不存在或不是有效的媒体文件
        ValueError: 路径参数无效
    """
    try:
        if not file_path:
            raise ValueError("文件路径不能为空")

        # 如果已经是绝对路径，验证后直接返回
        if os.path.isabs(file_path):
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"路径不是文件: {file_path}")
            return file_path

        # 构建完整路径
        full_path = os.path.join(FILE_ROOT, file_path)

        # 验证文件是否存在
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 验证是否为文件
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"路径不是文件: {file_path}")

        # 验证是否为媒体文件
        is_valid, _ = validate_media_type(full_path)
        if not is_valid:
            raise FileNotFoundError(f"文件不是有效的媒体文件: {file_path}")

        return full_path

    except (FileNotFoundError, ValueError):
        raise
    except Exception as e:
        print(f"获取媒体路径失败: {str(e)}")
        raise FileNotFoundError(f"获取媒体路径失败: {str(e)}")


def get_file_url(file_path, base_url="/static/files"):
    """
    获取文件的URL路径（用于Web访问）

    Args:
        file_path: 相对于FILE_ROOT的文件路径
        base_url: 基础URL路径

    Returns:
        str: 文件的URL路径
    """
    try:
        if not file_path:
            return None

        # 标准化路径分隔符为URL格式
        url_path = file_path.replace(os.path.sep, '/')
        return f"{base_url.rstrip('/')}/{url_path.lstrip('/')}"
    except Exception as e:
        print(f"生成文件URL失败: {str(e)}")
        return None


def create_directory(dir_path):
    """
    创建目录（如果不存在）

    Args:
        dir_path: 要创建的目录路径（相对于FILE_ROOT）

    Returns:
        bool: 创建成功返回True，失败返回False
    """
    try:
        if not dir_path:
            return False

        full_path = os.path.join(FILE_ROOT, dir_path)

        # 安全检查：确保路径在FILE_ROOT内
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


def move_file(src_path, dest_path):
    """
    移动文件

    Args:
        src_path: 源文件路径（相对于FILE_ROOT）
        dest_path: 目标文件路径（相对于FILE_ROOT）

    Returns:
        bool: 移动成功返回True，失败返回False
    """
    try:
        if not src_path or not dest_path:
            return False

        src_full_path = os.path.join(FILE_ROOT, src_path)
        dest_full_path = os.path.join(FILE_ROOT, dest_path)

        # 安全检查
        real_src_path = os.path.realpath(src_full_path)
        real_dest_path = os.path.realpath(dest_full_path)
        real_file_root = os.path.realpath(FILE_ROOT)

        if not (real_src_path.startswith(real_file_root) and real_dest_path.startswith(real_file_root)):
            print("安全错误：尝试在FILE_ROOT外移动文件")
            return False

        if not os.path.exists(src_full_path):
            return False

        # 确保目标目录存在
        dest_dir = os.path.dirname(dest_full_path)
        os.makedirs(dest_dir, exist_ok=True)

        # 移动文件
        os.rename(src_full_path, dest_full_path)
        return True
    except Exception as e:
        print(f"移动文件失败: {str(e)}")
        return False


def copy_file(src_path, dest_path):
    """
    复制文件

    Args:
        src_path: 源文件路径（相对于FILE_ROOT）
        dest_path: 目标文件路径（相对于FILE_ROOT）

    Returns:
        bool: 复制成功返回True，失败返回False
    """
    try:
        import shutil

        if not src_path or not dest_path:
            return False

        src_full_path = os.path.join(FILE_ROOT, src_path)
        dest_full_path = os.path.join(FILE_ROOT, dest_path)

        # 安全检查
        real_src_path = os.path.realpath(src_full_path)
        real_dest_path = os.path.realpath(dest_full_path)
        real_file_root = os.path.realpath(FILE_ROOT)

        if not (real_src_path.startswith(real_file_root) and real_dest_path.startswith(real_file_root)):
            print("安全错误：尝试在FILE_ROOT外复制文件")
            return False

        if not os.path.exists(src_full_path):
            return False

        # 确保目标目录存在
        dest_dir = os.path.dirname(dest_full_path)
        os.makedirs(dest_dir, exist_ok=True)

        # 复制文件
        shutil.copy2(src_full_path, dest_full_path)
        return True
    except Exception as e:
        print(f"复制文件失败: {str(e)}")
        return False


def cleanup_old_files(directory_path, days_old=30):
    """
    清理指定天数前的旧文件

    Args:
        directory_path: 目录路径
        days_old: 文件保留天数，默认30天

    Returns:
        tuple: (删除的文件数量, 释放的空间大小)
    """
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

