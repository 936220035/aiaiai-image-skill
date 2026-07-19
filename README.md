# AIAIAI Image Skill

让 Codex 或 Claude Code 通过 AIAIAI 中转站调用 `gpt-image-2`，生成图片或编辑已有图片，并把结果保存到本地。

## 当前支持

- 默认接口：`https://api.aiaiai001.com/v1`
- 默认模型：`gpt-image-2`
- 文生图：`POST /v1/images/generations`
- 图片编辑：`POST /v1/images/edits`
- 自动处理 `b64_json` 或图片 URL 返回结果
- Windows、macOS、Linux
- Codex 和 Claude Code Skill 安装
- 纯 Python 标准库，无需安装额外依赖

> `--size` 是提交给上游的请求尺寸，不等于保证输出一定是真 2K/4K。最终尺寸由实际上游模型决定。

## 1. 创建专用 Key

登录 [AIAIAI 中转站](https://api.aiaiai001.com)，创建新的 API Key，并把 Key 的分组选择为 **`GPT-Image`**。

分组由 Key 决定，脚本不能在请求里强行切换分组。如果 Key 选了其他分组，可能出现无权限或无可用渠道。

## 2. 安装

### Windows PowerShell

建议先下载再执行，便于检查脚本内容：

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/936220035/aiaiai-image-skill/main/install.ps1 -OutFile install.ps1
.\install.ps1
```

### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/936220035/aiaiai-image-skill/main/install.sh -o install.sh
bash install.sh
```

默认安装到 Codex。安装到 Claude Code：

```powershell
.\install.ps1 -Target claude
```

```bash
bash install.sh --target claude
```

同时安装到两者，把目标改成 `both`。安装完成后重启 Codex 或 Claude Code。

## 3. 安全配置 Key

不要把 Key 发到群里、截图里或提交到 GitHub。使用隐藏输入：

### Codex

```powershell
python "$HOME/.codex/skills/aiaiai-image/scripts/aiaiai_image.py" configure
```

### Claude Code

```powershell
python "$HOME/.claude/skills/aiaiai-image/scripts/aiaiai_image.py" configure
```

Key 默认保存在当前用户目录：

```text
~/.config/aiaiai-image/credentials.json
```

也可以使用环境变量 `AIAIAI_API_KEY`。仓库中不包含任何 API Key。

## 4. 检查权限

检查接口和模型权限，不会生成图片：

```powershell
python "$HOME/.codex/skills/aiaiai-image/scripts/aiaiai_image.py" check
```

## 5. 在 Codex 中使用

直接说：

```text
使用 $aiaiai-image，通过我的 AIAIAI 中转站生成一张写实风格的橘猫月球照片，1:1。
```

编辑图片：

```text
使用 $aiaiai-image 编辑这张图片，保留主体，把背景改成月球基地。
```

## 命令行使用

文生图：

```powershell
python "$HOME/.codex/skills/aiaiai-image/scripts/aiaiai_image.py" generate `
  --prompt "一只穿宇航服的橘猫站在月球上看电视，写实风格" `
  --size 1024x1024 `
  --out .\moon-cat.png
```

图片编辑：

```powershell
python "$HOME/.codex/skills/aiaiai-image/scripts/aiaiai_image.py" edit `
  --image .\input.png `
  --prompt "保持主体不变，把背景换成月球" `
  --out .\edited.png
```

## 重试和扣费提醒

脚本默认只请求一次。生图接口超时或连接中断时，上游可能已经完成并扣费，只是结果没有成功返回；盲目自动重试可能重复扣费。

确实需要重试时可以显式增加：

```text
--max-attempts 2
```

最多允许 3 次。

## 卸载本地 Key

```powershell
python "$HOME/.codex/skills/aiaiai-image/scripts/aiaiai_image.py" remove-key
```

## 参考项目

设计时参考了以下公开项目的使用思路，但本仓库代码为独立实现：

- [stevenjinlong/remote-imagegen](https://github.com/stevenjinlong/remote-imagegen)
- [QLHazyCoder/coder-api-image-skill](https://github.com/QLHazyCoder/coder-api-image-skill)
- [StevenLi-phoenix/imagegen-cli](https://github.com/StevenLi-phoenix/imagegen-cli)

## License

[MIT](LICENSE)
