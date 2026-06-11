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
