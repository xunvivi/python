import numpy as np
from core.stage1_degradation import Stage1Degradation
from core.stage2_degradation import Stage2Degradation
from core.stage3_degradation import Stage3Degradation  # 若存在
from utils.file_io import load_media, save_media  # 需实现文件读写工具函数


def composite_main_demo(media_path, media_type, stage1_params, stage2_params, stage3_params=None):
    """
    复合降质主流程：加载媒体 -> 多阶段降质 -> 保存结果
    :param media_path: 媒体文件路径（如 file 目录下的路径）
    :param media_type: image 或 video
    :param stage1_params: 第一阶段降质参数
    :param stage2_params: 第二阶段降质参数
    :param stage3_params: 第三阶段降质参数（可选）
    :return: 处理后文件路径等信息
    """
    try:
        # 加载媒体数据（转成 numpy 数组等格式，根据实际需求）
        media_data = load_media(media_path, media_type)

        # 初始化各阶段降质
        stage1 = Stage1Degradation(stage1_params)
        stage2 = Stage2Degradation(stage2_params)
        stage3 = Stage3Degradation(stage3_params) if stage3_params else None

        # 应用各阶段降质
        degraded_data = stage1.apply(media_data)
        degraded_data = stage2.apply(degraded_data)
        if stage3:
            degraded_data = stage3.apply(degraded_data)

        # 保存处理后的数据
        output_path = save_media(degraded_data, media_type, output_dir='processed/')

        return {
            "status": "success",
            "processed_path": output_path,
            "message": "复合降质处理完成"
        }
    except Exception as e:
        logger.error(f"复合降质处理失败: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }