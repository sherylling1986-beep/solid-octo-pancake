# Google Colab 自动展会视频生成项目

本项目用于从 Google Drive 现有素材中，自动生成一个 **30 秒展会宣传视频 MP4**。第一版不使用复杂 AI 模型，重点是稳定、易运行、可自动适配素材。

## 生成结果

运行 Notebook 后会输出：

```text
/content/drive/MyDrive/30秒快剪-JFEX展会速览/output/final_30s_exhibition_video.mp4
/content/drive/MyDrive/30秒快剪-JFEX展会速览/output/material_analysis.csv
```

视频规格：

- 1920 × 1080
- 30 fps
- MP4
- H.264
- 背景音乐优先使用 `music/` 中的音频；没有音乐时保留原视频声音

## 1. Google Drive 如何放素材

请在 Google Drive 的“我的云端硬盘”中创建或使用以下主文件夹：

```text
30秒快剪-JFEX展会速览/
```

程序会自动检查并创建这些子文件夹：

```text
30秒快剪-JFEX展会速览/
├── video/     # 展会视频素材
├── photo/     # 展会照片素材
├── logo/      # logo 图片素材
├── music/     # 背景音乐，可选
└── output/    # 自动输出视频、分析表、关键帧
```

不需要固定文件名。你可以把已有素材直接放入对应文件夹：

- `video/`：支持 `.mp4`、`.mov`、`.m4v`、`.avi`、`.mkv`、`.webm`
- `photo/`：支持 `.jpg`、`.jpeg`、`.png`、`.webp`、`.bmp`、`.tif`、`.tiff`
- `logo/`：支持常见图片格式，建议透明 `.png`
- `music/`：支持 `.mp3`、`.wav`、`.m4a`、`.aac`、`.flac`、`.ogg`

如果某个文件夹不存在，程序会自动创建。如果某类素材缺失，程序会自动跳过或用质量最高的其他素材替代。

## 2. Colab 如何运行

1. 将本项目文件上传到 Colab 环境，或在 Colab 中打开 `Generate_30s_Exhibition_Video.ipynb`。
2. 点击菜单 `Runtime` → `Run all`。
3. 第一步会自动挂载 Google Drive，请按提示授权。
4. Notebook 会安装依赖、创建素材目录、打印发现的素材、分析素材并生成视频。
5. 生成完成后，Notebook 最后会显示视频预览。

Notebook 会扫描：

```text
/content/drive/MyDrive/30秒快剪-JFEX展会速览/video/
/content/drive/MyDrive/30秒快剪-JFEX展会速览/photo/
/content/drive/MyDrive/30秒快剪-JFEX展会速览/logo/
/content/drive/MyDrive/30秒快剪-JFEX展会速览/music/
```

## 3. 如何获得最终视频

生成完成后，到 Google Drive 下载：

```text
我的云端硬盘/30秒快剪-JFEX展会速览/output/final_30s_exhibition_video.mp4
```

素材分析表在：

```text
我的云端硬盘/30秒快剪-JFEX展会速览/output/material_analysis.csv
```

分析表会记录：

- 文件名
- 类型
- 时长
- 分辨率
- 质量评分
- 用途
- 自动截取的视频关键帧路径

## 4. 如何替换素材

如果想换成新素材：

1. 删除或替换 Google Drive 对应文件夹中的旧素材。
2. 保持文件夹名称不变：`video/`、`photo/`、`logo/`、`music/`。
3. 重新运行 Notebook。
4. 新视频会覆盖输出到 `output/final_30s_exhibition_video.mp4`。

你也可以追加更多素材。程序会根据文件名关键词、分辨率、清晰度和视频时长自动选择更适合的素材。

## 自动剪辑逻辑

程序会自动生成以下 30 秒结构：

| 时间 | 内容 | 优先素材 |
| --- | --- | --- |
| 0-3 秒 | 开场 | 展馆入口、展会现场、人流画面 |
| 3-10 秒 | 展位展示 | 企业展位、展馆环境 |
| 10-20 秒 | 产品展示 | 产品图片、产品视频 |
| 20-27 秒 | 商务交流 | 客户交流、人流、活动现场 |
| 27-30 秒 | 品牌结束页 | logo 图片 |

程序会根据素材文件名和所在文件夹中的关键词推断用途。例如：`入口`、`展位`、`产品`、`交流`、`人流`、`logo` 等。如果没有匹配素材，会自动用质量评分最高的素材补位。

## 本地运行方式

也可以在本地命令行运行：

```bash
python -m pip install -r requirements.txt
python generate_video.py \
  --input-dir "/path/to/30秒快剪-JFEX展会速览"
```

指定输出路径：

```bash
python generate_video.py \
  --input-dir "/path/to/30秒快剪-JFEX展会速览" \
  --output "/path/to/final_30s_exhibition_video.mp4"
```

## 文件说明

- `Generate_30s_Exhibition_Video.ipynb`：Google Colab Notebook，一键挂载 Drive、扫描素材、分析素材、生成视频。
- `generate_video.py`：核心视频生成程序。
- `requirements.txt`：Colab 和本地运行所需依赖。
- `README.md`：中文使用说明。
