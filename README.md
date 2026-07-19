# AIAIAI 生图 Skill

通过 AIAIAI 中转站调用 `gpt-image-2` 生图，Codex、Claude Code 都可以使用。

## 最简单的使用方法

### 第一步：把仓库地址发给 AI

直接对 Codex 或 Claude Code 说：

```text
请帮我安装这个仓库中的生图 Skill：
https://github.com/936220035/aiaiai-image-skill
Skill 位于 skills/aiaiai-image，安装后告诉我是否需要重启。
```

### 第二步：创建一个专用生图 Key

登录 [AIAIAI 中转站](https://api.aiaiai001.com) 创建 Key，建议设置：

- 分组：`GPT-Image`
- 限制模型：`gpt-image-2`
- 限制一个较小的可用金额

不要使用主账号长期大额 Key。

### 第三步：把 Key 和生图要求发给 AI

```text
请调用 AIAIAI 生图 Skill，使用此密钥：“sk-.........”，
帮我生成一张穿宇航服的橘猫站在月球上看电视的图片，1:1，写实风格。
并帮我把密钥保存在本地，下次不用再次发送。
```

AI 会保存这个 Key，并继续生成图片。以后只需要说：

```text
请调用 AIAIAI 生图 Skill，帮我生成一张……
```

如果使用计划模式，可以让 AI 先询问画面比例、风格、文字和构图，再开始生成。

## 支持功能

- 文生图
- 图片编辑
- 自动保存返回的 Base64 或 URL 图片
- 默认接口：`https://api.aiaiai001.com/v1`
- 默认模型：`gpt-image-2`
- Windows、macOS、Linux

> 请求2K或4K不代表上游一定返回真2K/4K，最终以图片实际像素为准。

## 手动安装（备用）

正常情况下直接把仓库地址发给 AI 安装即可。

Windows：

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/936220035/aiaiai-image-skill/main/install.ps1 -OutFile install.ps1
.\install.ps1
```

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/936220035/aiaiai-image-skill/main/install.sh -o install.sh
bash install.sh
```

## 安全提醒

- 只发送限制模型、限制金额的专用生图 Key。
- 不要把 Key 发到群聊、公开 Issue 或 GitHub 仓库。
- Skill 默认只请求一次，避免超时后自动重试造成重复扣费。
- Key 保存在用户自己的电脑，不会写入本仓库。

## License

[MIT](LICENSE)
