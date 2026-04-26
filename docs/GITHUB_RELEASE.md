# GitHub 仓库与 Release 交付

本文用于维护者把项目整理成 GitHub 仓库，并向学生发布可下载版本。

## 1. 仓库建议

推荐提交以下内容：

- `app/`
- `templates/`
- `static/`
- `scripts/`
- `packaging/`
- `docs/`
- `tests/`
- `README.md`
- `.gitignore`
- `pyproject.toml`

不要提交：

- `.venv/`
- `workspace/`
- `tmp/`
- `.pytest_cache/`
- `.ruff_cache/`
- `dist/`
- 本地生成的 `*.zip`

## 2. 发布前检查

开发安装：

```bash
python -m pip install -e ".[dev,ai]"
```

运行测试：

```bash
python -m pytest -q
```

检查代码风格：

```bash
python -m ruff check app scripts packaging tests
```

需要 OCR 验证时：

```bash
python -m pip install -e ".[ocr]"
python scripts/acceptance_check.py --rounds 5 --require-ai
```

## 3. 生成 Release 附件

```bash
python packaging/build_release.py
```

默认生成：

```text
dist/lite-deeplearning-studio-source.zip
```

这个脚本是轻量源码打包脚本，不引入 PyInstaller、Electron 或其他重型打包器。

## 4. GitHub Release 内容模板

标题示例：

```text
Lite DeepLearning Studio v0.1.0
```

Release 说明示例：

```markdown
## 安装路径

- 基础安装：`python -m pip install -e .`
- OCR 安装：`python -m pip install -e ".[ocr]"`
- 开发安装：`python -m pip install -e ".[dev,ai,ocr]"`

## 启动

`python scripts/start_studio.py`

打开 `http://127.0.0.1:8000`。

## 附件

下载 `lite-deeplearning-studio-source.zip`，解压后按 `docs/INSTALLATION.md` 操作。
```

## 5. 学生交付建议

给学生的最短说明：

```text
1. 下载 Release 附件 lite-deeplearning-studio-source.zip。
2. 解压并进入目录。
3. 执行 python -m pip install -e .
4. 执行 python scripts/start_studio.py。
5. 打开 http://127.0.0.1:8000。
```
