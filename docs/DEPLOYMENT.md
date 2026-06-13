# 服务器部署指南（Docker）

Lite DeepLearning Studio 可以部署到学校机房或云服务器上，全班学生用浏览器访问同一个地址，不需要在每台学生机上安装。

## 前置条件

- 一台 Linux 服务器（或装有 Docker Desktop 的 Windows/macOS 主机）。
- 已安装 Docker 和 Docker Compose 插件（`docker compose version` 能正常输出）。

## 一条命令部署

在项目根目录执行：

```bash
docker compose up -d --build
```

完成后访问：

```text
http://<服务器IP>:8000
```

学生项目数据保存在宿主机的 `./workspace` 目录，容器重建不会丢失。

## 教学数据集（可选）

平台第 1 步「准备数据」里的「从整理好的数据集导入」下拉，读取的是一个**整理好的教学数据集目录**。这个目录体积较大（几个 GB），不放进代码仓库，也不进 git，需要单独迁移。

- 默认位置：项目根目录下的 `datasets/`（已在 `.gitignore` 中忽略）。
- 可用环境变量 `LDS_DATASETS_ROOT` 指向别处。
- **目录不存在也不影响运行**——只是导入下拉为空，学生仍可手动上传数据。

### 本机 / 开发机

把整理好的数据集包放到 `./datasets`，或建一个软链接指向它：

```bash
ln -s /path/to/OpenHydra-平台数据集 datasets
```

### 服务器（Docker）

`docker-compose.yml` 已经把宿主机的 `./datasets` 以只读方式挂载到容器，并设置了 `LDS_DATASETS_ROOT=/app/datasets`。把数据集包放到服务器的 `./datasets` 即可：

```bash
# 在服务器项目根目录
mkdir -p datasets
rsync -av --progress 整理好的数据集包/ datasets/
docker compose up -d --build
```

> 数据集多为几 GB，首次同步较慢。若远程只给学生手动上传用，可以不放数据集，留空即可。

## 选择竞赛版本和端口

通过环境变量切换，例如部署智能博物轻量版到 8080 端口：

```bash
LDS_EDITION=smart_museum LDS_PORT=8080 docker compose up -d --build
```

`LDS_EDITION` 可选值：`all`（默认，两个竞赛都显示）、`smart_museum`、`future_creator`。

也可以在同一台服务器上为两个比赛各部署一份：复制目录后分别用不同的 `LDS_PORT` 启动。

## 常用运维命令

```bash
docker compose logs -f          # 查看运行日志
docker compose restart          # 重启服务
docker compose down             # 停止并删除容器（workspace 数据保留）
docker compose up -d --build    # 更新代码后重新构建并启动
```

## 数据备份

所有学生项目（数据集、模型、导出包）都在 `workspace/` 目录，直接打包备份即可：

```bash
tar czf workspace-backup-$(date +%Y%m%d).tar.gz workspace/
```

## 注意事项

- 服务面向校园局域网设计，没有账号系统；不要直接暴露到公网。如需公网访问，请在前面加一层带认证的反向代理（如 Nginx + Basic Auth）。
- OCR 拍照识别依赖（EasyOCR/Torch）默认不装进镜像，文字查错功能不受影响。
