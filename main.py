# 使用前记得替换成你自己实际的目录
BASE_DIR = r"D:\down"

# 我知道写的很乱别骂了别骂了
# biliup.exe 来自项目 biliup-rs，
# 如果你觉得用这个我提供的二进制很膈应也可以自己去他们的仓库下载一个替换上
# （如果碰巧你下了同一个版本应该哈希都是一致的）

TARGET_DIR = f"{BASE_DIR}"
SCAN = 1800


from time import sleep
from datetime import datetime
from pathlib import Path
from loguru import logger
from pydantic import BaseModel
from subprocess import run
from os import remove


# 单个文件的元数据实体
class Metadata(BaseModel):
    room_id: str
    date: int
    file_start_time: int
    title: str


# 投稿参数数据实体
class SubmitParams(BaseModel):
    copyright: int = 2
    # 封面
    cover: Path
    # 视频简介
    desc: str
    # 转载来源
    source: str
    # 视频标签
    tag: str
    # 投稿分区
    tid: int
    # 视频标题
    title: str

    def export(self):
        params_list = []

        for cmd_key, cmd_value in self.model_dump().items():
            params_list.append(f"--{cmd_key} {cmd_value}")
        return " ".join(params_list)


# 用于记录录制与上传状态的dict
# room_id: 上一次修改时间
data_update: dict[str, datetime] = {}


# 解析路径中信息的函数
def file_path_parse(path: Path) -> Metadata:
    file_name = path.name
    file_name_list = file_name.split("-")
    meta = Metadata(
        room_id=file_name_list[1],
        date=int(file_name_list[2]),
        file_start_time=int(file_name_list[3]),
        title="".join(file_name_list[5].split(".")[:-1]),
    )
    return meta


# 整合各个文件的元数据，保留最早的一份作为投稿数据
def meta_merge(meta_list: list[Metadata]) -> Metadata:
    final_meta = meta_list[0]
    for meta_item in meta_list:
        if meta_item.date < final_meta.date:
            if meta_item.file_start_time < final_meta.file_start_time:
                final_meta.date = meta_item.date
                final_meta.file_start_time = meta_item.file_start_time
                final_meta.title = meta_item.title
    return final_meta


# 上传命令构造函数
def upload(name: str, meta: Metadata, video_files: list[Path], cover_path: Path):

    live_url = f"https://live.bilibili.com/{meta.room_id}"
    title = f"[直播回放][{name}][{meta.date}{meta.file_start_time}][{meta.title}][{meta.room_id}]"
    title = title.replace("\"", "")
    title = f"\"{title}\""

    data = SubmitParams(
        cover=cover_path,
        desc=f"\"关注{name}谢谢喵 {live_url}\"",
        source=live_url,
        tag=f"vup,{name},虚拟主播,直播回放",
        tid=0,
        title=title
    )

    files = ' '.join([video.as_posix() for video in video_files])

    logger.debug(data)
    cmd = f"./biliup upload {files} {data.export()}"
    logger.debug(cmd)
    try:
        run(cmd)
    except Exception as e:
        logger.error(e)


# 上传执行函数
def run_upload(path: Path):
    logger.info(f"开始上传 {path.name}")

    name = path.name.split("-")[-1]
    video_files: list[Path] = [file for file in path.glob("*.flv")]
    cover_list: list[Path] = [file for file in path.glob("*.jpg")]

    meta_list = []
    for file in video_files:
        meta = file_path_parse(file)
        meta_list.append(meta)

    if meta_list:
        final_meta = meta_merge(meta_list)
        logger.debug(final_meta)

        if cover_list:
            cover_path = cover_list[-1]
        else:
            cover_path = Path(rf"{BASE_DIR}\新建位图图像.jpg")

        upload(name, final_meta, video_files, cover_path)

        for video in video_files:
            remove(video)
        for cover in cover_list:
            remove(cover)

    else:
        logger.info(f"{path.name} 没有文件，跳过")


# 主循环
while True:
    logger.info(f"休眠 {SCAN} 秒")
    sleep(SCAN)

    logger.debug(data_update)

    for item in Path(TARGET_DIR).glob("*/"):
        item: Path

        key = item.as_posix()
        current_modify_time = datetime.fromtimestamp(item.stat().st_mtime)

        if key not in data_update:
            data_update[key] = current_modify_time
            continue

        if data_update[key] != current_modify_time:
            data_update[key] = current_modify_time
        else:
            run_upload(item)
