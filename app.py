import os
import uvicorn
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
import subprocess
from pathlib import Path
import logging
from fastapi import UploadFile, File
import shutil

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入核心处理函数和工具
from single_main import single_main_demo
from composite_main import composite_main_demo
from utils.file_io import (
    validate_media_type,
    get_media_path,
    MEDIA_ROOT,
    get_file_size,
    generate_output_filename
)

app = FastAPI(title="图像/视频降质可视化系统")

# 添加CORS中间件解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境配置，生产环境需限制域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 数据模型定义（核心调整：统一参数结构）
class DegradationConfig(BaseModel):
    """单个退化阶段的标准配置模型"""
    name: str = Field(..., description="退化类型（如'composite'或具体退化类型）")
    params: Dict = Field(..., description="退化参数字典")


class SingleDegradationRequest(BaseModel):
    media_path: str  # file目录下的相对路径
    media_type: str  # "image" 或 "video"
    degradation_type: str
    params: Optional[Dict] = {}


class CompositeDegradationRequest(BaseModel):
    """复合退化请求模型（与前端参数结构完全匹配）"""
    media_path: str
    media_type: str
    first_config: DegradationConfig  # 第一阶段配置
    second_config: DegradationConfig  # 第二阶段配置
    third_config: Optional[DegradationConfig] = None  # 第三阶段可选配置


class FileDeleteRequest(BaseModel):
    file_path: str  # file目录下的相对路径


class FileListRequest(BaseModel):
    subdir: Optional[str] = ""  # 子目录，默认为根目录


# 单个降质处理接口
@app.post("/api/single-degradation")
async def process_single_degradation(request: SingleDegradationRequest):
    try:
        logger.info(f"开始单降质处理: {request.media_path}, 类型: {request.degradation_type}")

        # 获取文件绝对路径
        try:
            full_path = get_media_path(request.media_path)
            logger.info(f"文件路径解析成功: {full_path}")
        except FileNotFoundError as e:
            logger.error(f"文件不存在: {str(e)}")
            raise ValueError(f"文件不存在: {str(e)}")

        # 验证媒体类型
        if not validate_media_type(full_path, request.media_type):
            msg = f"文件 {request.media_path} 不是有效的{request.media_type}类型"
            logger.error(msg)
            raise ValueError(msg)

        # 调用处理函数
        result = single_main_demo(
            media_path=full_path,
            media_type=request.media_type,
            degradation_type=request.degradation_type,
            degradation_params=request.params
        )

        logger.info(f"单降质处理成功: {request.media_path}")
        return {"status": "success", "data": result}

    except Exception as e:
        logger.error(f"单降质处理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # 确保媒体根目录存在
        if not MEDIA_ROOT.exists():
            MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

        # 保存文件到 MEDIA_ROOT 目录
        file_path = MEDIA_ROOT / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 返回文件相对路径
        relative_path = str(file_path.relative_to(MEDIA_ROOT))
        logger.info(f"文件上传成功: {relative_path}")

        return {
            "status": "success",
            "data": {
                "file_path": relative_path,
                "file_name": file.filename,
                "content_type": file.content_type
            }
        }
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


# 复合降质处理接口（核心调整：匹配前端参数结构）
@app.post("/api/composite-degradation")
async def process_composite_degradation(request: CompositeDegradationRequest):
    try:
        logger.info(f"开始复合降质处理: {request.media_path}")

        # 获取文件绝对路径
        try:
            full_path = get_media_path(request.media_path)
            logger.info(f"文件路径解析成功: {full_path}")
        except FileNotFoundError as e:
            logger.error(f"文件不存在: {str(e)}")
            raise ValueError(f"文件不存在: {str(e)}")

        # 验证媒体类型
        if not validate_media_type(full_path, request.media_type):
            msg = f"文件 {request.media_path} 不是有效的{request.media_type}类型"
            logger.error(msg)
            raise ValueError(msg)

        # 转换配置为字典（Pydantic模型转普通字典）
        first_config = request.first_config.dict()
        second_config = request.second_config.dict()
        third_config = request.third_config.dict() if request.third_config else None

        # 调用复合处理函数
        result = composite_main_demo(
            media_path=full_path,
            media_type=request.media_type,
            first_config=first_config,
            second_config=second_config,
            third_config=third_config
        )

        logger.info(f"复合降质处理成功: {request.media_path}")
        return {"status": "success", "data": result}

    except Exception as e:
        logger.error(f"复合降质处理失败: {str(e)}", exc_info=True)
        # 确保错误信息为字符串类型
        raise HTTPException(status_code=400, detail=str(e))


# 获取媒体文件信息接口
@app.post("/api/media-info")
async def get_media_info(request: dict):
    try:
        file_path = request.get("file_path")
        if not file_path:
            raise ValueError("未提供file目录下的文件路径")

        logger.info(f"获取媒体信息: {file_path}")
        full_path = get_media_path(file_path)
        size_bytes, size_human = get_file_size(full_path)

        # 使用ffprobe获取详细信息
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "stream=width,height,r_frame_rate,duration,codec_name,bit_rate,pix_fmt",
                    "-show_format", "-of", "json", str(full_path)
                ],
                capture_output=True, text=True, check=True
            )
            ffprobe_data = json.loads(result.stdout)

            media_info = {
                "width": None, "height": None, "format": ffprobe_data.get("format", {}).get("format_name", ""),
                "duration": None, "fps": None, "video_codec": None, "audio_codec": None,
                "bitrate": None, "color_space": None, "bit_depth": None,
                "file_size": size_bytes, "file_size_human": size_human, "file_path": file_path
            }

            # 解析流信息
            for stream in ffprobe_data.get("streams", []):
                if stream.get("codec_type") == "video":
                    media_info["width"] = stream.get("width")
                    media_info["height"] = stream.get("height")
                    media_info["video_codec"] = stream.get("codec_name")
                    if "r_frame_rate" in stream:
                        num, den = map(int, stream["r_frame_rate"].split('/'))
                        media_info["fps"] = round(num / den, 2) if den else None
                    if "pix_fmt" in stream:
                        media_info["color_space"] = stream["pix_fmt"]
                        media_info["bit_depth"] = 10 if '10' in stream["pix_fmt"] else 8
                elif stream.get("codec_type") == "audio":
                    media_info["audio_codec"] = stream.get("codec_name")
                if not media_info["bitrate"] and "bit_rate" in stream:
                    media_info["bitrate"] = int(stream["bit_rate"])

            media_info["duration"] = round(float(ffprobe_data["format"]["duration"]),
                                           2) if "duration" in ffprobe_data.get("format", {}) else None
            return media_info

        except Exception as e:
            logger.warning(f"ffprobe获取信息失败: {str(e)}")
            return {
                "width": None, "height": None,
                "format": os.path.splitext(full_path)[1].lower().lstrip('.'),
                "file_size": size_bytes, "file_size_human": size_human,
                "file_path": file_path,
                "warning": "无法获取详细媒体信息，请确保已安装ffmpeg"
            }

    except Exception as e:
        logger.error(f"获取媒体信息失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


# 获取文件接口
@app.get("/api/file")
async def get_file(path: str):
    try:
        logger.info(f"获取文件: {path}")
        full_path = get_media_path(path)
        return FileResponse(
            full_path,
            filename=os.path.basename(full_path),
            media_type="application/octet-stream"
        )
    except Exception as e:
        logger.error(f"获取文件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


# 获取文件列表接口
@app.post("/api/file-list")
async def get_file_list(request: FileListRequest):
    try:
        target_dir = MEDIA_ROOT / request.subdir
        target_dir = target_dir.resolve()
        if not str(target_dir).startswith(str(MEDIA_ROOT)):
            raise ValueError("不允许访问file目录外的路径")

        if not target_dir.exists() or not target_dir.is_dir():
            raise ValueError(f"目录不存在: {request.subdir}")

        file_list = []
        for item in target_dir.iterdir():
            if item.is_file():
                try:
                    is_image = validate_media_type(str(item), "image")
                    is_video = validate_media_type(str(item), "video")
                    if is_image or is_video:
                        size_bytes, size_human = get_file_size(str(item))
                        rel_path = str(item.relative_to(MEDIA_ROOT))
                        file_list.append({
                            "name": item.name, "path": rel_path,
                            "type": "image" if is_image else "video",
                            "size": size_bytes, "size_human": size_human,
                            "modified": item.stat().st_mtime
                        })
                except Exception:
                    continue

        file_list.sort(key=lambda x: x["modified"], reverse=True)
        return {
            "status": "success",
            "data": {
                "current_dir": request.subdir,
                "parent_dir": str(target_dir.parent.relative_to(MEDIA_ROOT)) if target_dir != MEDIA_ROOT else "",
                "files": file_list
            }
        }
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


# 删除文件接口
@app.post("/api/files/delete")
async def delete_file(request: FileDeleteRequest):
    try:
        logger.info(f"删除文件: {request.file_path}")
        full_path = get_media_path(request.file_path)
        if not os.path.isfile(full_path):
            raise ValueError(f"{request.file_path}不是文件，无法删除")

        os.remove(full_path)
        return {"status": "success", "message": f"文件已删除: {request.file_path}"}
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


# 健康检查接口
@app.get("/health")
async def health_check():
    media_exists = MEDIA_ROOT.exists()
    media_is_dir = MEDIA_ROOT.is_dir() if media_exists else False
    file_count = 0
    if media_exists and media_is_dir:
        try:
            file_count = len([f for f in MEDIA_ROOT.iterdir() if f.is_file()])
        except Exception:
            file_count = -1

    return {
        "status": "healthy",
        "service": "degradation_vis_system",
        "media_root": str(MEDIA_ROOT),
        "media_root_exists": media_exists,
        "media_root_is_dir": media_is_dir,
        "approx_file_count": file_count
    }


if __name__ == "__main__":
    logger.info(f"媒体文件根目录: {MEDIA_ROOT}")
    logger.info("启动服务...")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)