# 星火同行 · Android 端

**Xinghuo Companion — Android** ｜ 包名 `cn.xinghuo.companion` ｜ 版本 1.0.0（versionCode 10000）

面向青年用户的思政创新赛道参赛作品：一个装在口袋里的 AI 成长伙伴。应用把界面、角色、题库全部打进安装包，在手机自身进程内运行 Python 服务——不需要连接电脑、不需要安装 Python、不需要填写任何 API Key。

## 功能特性

**完全离线可用**
- 角色互动：三段动作视频（打招呼 / 思考 / 互动）与七段互动语音，随包安装
- 思政闯关：题库答题游戏，闯关进度本地保存
- 草稿箱：聊天草稿自动保存，退出不丢

**在线能力免密钥**
- 免费在线对话：沿用 Pollinations 公共免 Key 接口（旧版匿名文字接口，实测返回 gpt-oss-20b），流式输出、自动剥离思考过程
- 在线甜声：edge-tts 合成「轻快」「童声」两种音色，本机缓存复用
- 系统语音桥接：语音输入调用手机系统识别服务；朗读可回落系统中文 TTS

**端内 Python 服务**
- 基于 Chaquopy 在应用进程内运行 Python 3.13，通过 `127.0.0.1:18766` 同源 HTTP 接口提供页面、对话、语音与学习进度服务
- 关闭接口只响应 405，引导用户用返回键退出

## 技术栈

| 层 | 技术 |
|---|---|
| 应用框架 | Java 17，AGP 8.9.2，minSdk 26（Android 8.0），targetSdk 35 |
| ABI | arm64-v8a（主）+ x86_64（测试） |
| Python 运行时 | Chaquopy 17.0.0 + Python 3.13（`pyc` 编译关闭） |
| 界面 | 系统 WebView + 本地静态资源（`assets/web`）+ JS Bridge |
| 在线对话 | Pollinations 免 Key 接口（`text.pollinations.ai/openai`） |
| 在线语音 | edge-tts 7.2.8 + aiohttp 3.14.3 网络栈（纯 Python wheels） |
| 语音识别 | Android `SpeechRecognizer`（系统服务） |

## 目录结构

```
├── app/                          # Android 应用模块
│   ├── build.gradle              # 应用配置（签名、Chaquopy、依赖）
│   └── src/main/
│       ├── AndroidManifest.xml   # 权限：联网 / 网络状态 / 录音
│       ├── java/cn/xinghuo/companion/MainActivity.java   # WebView + 语音桥接
│       ├── python/               # 端内 Python 服务
│       │   ├── mobile_server.py     # 进程内服务入口（127.0.0.1:18766）
│       │   ├── static_server.py     # 页面 / 对话 / 进度 HTTP 服务
│       │   ├── model_provider.py    # Pollinations 免 Key 对话客户端
│       │   └── tts_server.py        # edge-tts 合成与缓存
│       ├── assets/web/           # 移动端页面（agent 聊天 / game 闯关 / 视频 / 语音）
│       └── res/                  # 图标、字符串、样式、网络安全配置
├── mobile/                       # 电脑端页面源（sync_assets.py 的同步来源）
├── third_party/edge-tts/         # edge-tts 7.2.8 原始源码（LGPL，含许可证）
├── wheels/                       # 纯 Python 网络依赖 wheels
├── tests/                        # 移动端检查 / 预览服务 / APK 校验脚本
├── sync_assets.py                # 从电脑项目同步 Web 资源（仅原作者使用）
└── BUILD.md                      # 官方构建说明
```

## 构建

详细说明见 [BUILD.md](BUILD.md)。要点：

1. 安装 JDK 17 或 21、Android SDK Platform 35、Build Tools 35.0.0
2. 准备 Python 3.13（可用 Anaconda，无需改动全局环境）
3. 设置 `JAVA_HOME`、`ANDROID_HOME`，`XINGHUO_BUILD_PYTHON` 指向 Python 3.13 可执行文件绝对路径
4. 执行 `gradlew.bat assembleDebug`（首次构建会下载 Gradle、Chaquopy 与 Python 依赖）

`app/src/main/assets/web` 已包含同步后的完整移动端页面，构建时无需再运行 `sync_assets.py`。

## 发布签名

发布构建读取**项目上级目录**的 `android-signing/signing.properties`（不在本仓库内）：

```properties
storeFile=签名文件绝对路径（正斜杠）
storePassword=自己的签名密码
keyAlias=xinghuo
```

签名文件与密码不随源码或 APK 分发。更新已有安装必须使用原签名并递增 `versionCode`。

## 测试

- `tests/mobile_checks.cjs`：移动端布局、聊天、自动朗读、系统语音桥接、草稿、游戏进度检查
- `tests/preview_server.py`：用实际打包的 Python 依赖预览移动页面
- `tests/verify_apk.py`：APK 完整性校验

APK 使用系统 WebView，需要正常且更新的 WebView 组件。

## 隐私与权限

应用仅申请三项权限：网络状态、联网、录音（录音在点击麦克风时动态申请）。

- 聊天内容发送至 Pollinations 公共服务
- 在线朗读文本发送至 Microsoft Edge 语音服务
- 不读取、不保存、不上传任何用户密钥；闯关进度与偏好仅存于应用私有目录

## 第三方组件与许可

- `third_party/edge-tts`：edge-tts 7.2.8 原始 Python 源码（LGPL），可替换后重新构建
- 应用内「第三方版权许可」页（`assets/web/licenses.html` 与 `third-party-notices.txt`）保留全部归属信息

## 相关仓库

- 电脑端 / PV 工程：[M4from404/agent](https://github.com/M4from404/agent)
