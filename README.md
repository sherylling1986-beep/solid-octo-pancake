# 30 秒 JFEX 展会宣传视频自动生成器

这个项目用于在 **Google Colab** 中自动读取 Google Drive 素材，并生成一个 30 秒横版展会宣传视频。你只需要把素材放进指定分类文件夹，运行 Notebook，即可输出 MP4 成片。

项目选择 **MoviePy + FFmpeg**：

- 适合 Google Colab 运行，不需要搭建复杂渲染服务。
- 可自动读取图片、视频、音乐并合成为 MP4。
- 避免手动剪辑，适合展会快剪模板化生成。

## 输出规格

- 分辨率：1920 × 1080
- 帧率：30 fps
- 时长：30 秒
- 格式：MP4 / H.264 / AAC
- 输出路径：`Exhibition_30s_Video/output/final_30s_exhibition_video.mp4`

## 视频结构

| 时间 | 内容 | 素材来源 |
| --- | --- | --- |
| 0-3 秒 | 展馆入口照片 | `展馆入口照片` |
| 3-8 秒 | 展位照片 | `展位照片` |
| 8-27 秒 | 展馆内视频 | `展馆内视频` |
| 27-30 秒 | logo 结尾 | `展会logo` |

系统会自动添加以下英文字幕：

1. Exhibition Highlights
2. Hunan Pavilion
3. Featured Products
4. Connecting with Global Buyers
5. Business Opportunities
6. JYX EXPO

背景音乐会自动读取 `music` 文件夹中的第一首音频文件。如果没有音乐文件，也可以生成无音乐版本。

## Google Drive 素材放置方式

请在 Google Drive 的“我的云端硬盘”中创建以下目录：

```text
30秒快剪-JFEX展会速览/
├── 展位照片/
├── 人流照片/
├── 展馆入口照片/
├── 展会主题背景图片/
├── 展会logo/
├── 展馆内视频/
├── music/
└── 视频剪辑文案word文档/
```

### 文件要求

- `展馆入口照片`：放 1 张或多张入口照片，支持 `.jpg`、`.jpeg`、`.png`、`.webp`。
- `展位照片`：放 1 张或多张展位照片，支持 `.jpg`、`.jpeg`、`.png`、`.webp`。
- `展馆内视频`：放至少 1 个展馆内视频，支持 `.mp4`、`.mov`、`.m4v`、`.avi`、`.mkv`、`.webm`。
- `展会logo`：放 1 张或多张 logo 图片，建议透明 `.png`。
- `music`：放至少 1 首背景音乐，支持 `.mp3`、`.wav`、`.m4a`、`.aac`、`.flac`、`.ogg`。
- `人流照片`、`展会主题背景图片`、`视频剪辑文案word文档`：当前模板保留这些文件夹，方便后续扩展；本版 30 秒结构暂不强制使用。

> 提示：同一个分类文件夹内放多张素材时，系统会自动随机选择一张。默认随机种子固定为 `2026`，所以同一批素材会得到可复现的结果；你也可以在命令中修改 `--seed`。

## 如何在 Google Colab 运行

1. 打开 `notebooks/Generate_30s_Exhibition_Video.ipynb`。
2. 点击 Colab 顶部菜单：`Runtime` → `Run all`。
3. 第一次运行时，Colab 会要求授权访问 Google Drive，请按提示登录并授权。
4. Notebook 会安装依赖、挂载 Google Drive、检查素材并生成视频。
5. 生成完成后，到 Google Drive 下载：

```text
我的云端硬盘/Exhibition_30s_Video/output/final_30s_exhibition_video.mp4
```

## 在本地或 GitHub Actions 中运行

如果你已经把素材同步到本地，也可以直接运行：

```bash
python -m pip install -r requirements.txt
python src/generate_exhibition_video.py \
  --input-dir "/path/to/30秒快剪-JFEX展会速览" \
  --output "/path/to/Exhibition_30s_Video/output/final_30s_exhibition_video.mp4"
```

## 常见问题

### 1. 找不到素材怎么办？

请确认文件夹名称和 README 中完全一致，尤其是：`30秒快剪-JFEX展会速览`、`展馆入口照片`、`展位照片`、`展馆内视频`、`展会logo`。

### 2. 视频不足 19 秒怎么办？

脚本会自动循环展馆内视频，直到填满 8-27 秒这一段。

### 3. 图片比例不是 16:9 怎么办？

脚本会自动居中裁切并缩放到 1920 × 1080，同时添加轻微推近效果。

### 4. 可以更换字幕吗？

可以。请编辑 `src/generate_exhibition_video.py` 中的 `DEFAULT_CAPTIONS`。
