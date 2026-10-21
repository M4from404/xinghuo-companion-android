# 星火同行 Android 1.0.0

适用于 Android 8.0 及以上的 64 位 ARM 手机，同时包含 x86_64 测试架构。
界面、角色图片、三段动作视频、七段互动语音和思政题库随包安装。
应用在手机自身进程中运行 Python 服务，无需连接电脑、安装 Python 或填写 API Key。
在线模型沿用 Pollinations 公共免 Key 接口；在线朗读沿用 edge-tts。

## 构建

1. 安装 JDK 17 或 21、Android SDK Platform 35 和 Build Tools 35.0.0。
2. 准备 Python 3.13，可使用 Anaconda；无需改动全局 Conda 环境。
3. 设置 `JAVA_HOME`、`ANDROID_HOME`，并将 `XINGHUO_BUILD_PYTHON` 设为 Python 3.13 可执行文件的绝对路径。
4. 执行 `gradlew.bat assembleDebug`。首次构建会下载 Gradle、Chaquopy 和 Python 依赖。

`app/src/main/assets/web` 已经包含同步后的完整移动端页面；构建时无需再次运行 `sync_assets.py`。
`sync_assets.py` 仅供原作者从电脑项目更新资源，使用前修改其 `source` 路径。
`wheels` 是纯 Python 网络依赖，避免依赖特定安卓机器的编译扩展。

## 发布签名

发布构建读取项目上级目录 `android-signing/signing.properties`：

    storeFile=签名文件绝对路径（使用正斜杠）
    storePassword=自己的签名密码
    keyAlias=xinghuo

执行 `gradlew.bat assembleRelease lintRelease`。签名文件和密码不在源码包或 APK 中。
更新已有安装时，必须使用原签名并增加 `versionCode`；自行生成新签名只能作为新的安装分发。

## 测试与说明

- `tests/mobile_checks.cjs`：移动端布局、聊天、自动朗读、系统语音桥接、草稿、游戏进度测试。
- `tests/preview_server.py`：使用实际打包的 Python 依赖运行移动页面预览。
- APK 使用 Android 系统 WebView，需要正常且更新的系统 WebView。
- 语音输入调用手机系统识别服务；没有此服务的手机可通过输入法语音输入或打字。
- 离线可用角色互动、题库、闯关进度；模型聊天和在线甜声需要联网。
- 聊天内容发给 Pollinations，朗读文本发给 Microsoft Edge 语音服务。
- 应用权限仅网络状态、联网、录音；录音权限在点击麦克风时申请。
- 第三方版权许可保留在应用中。`third_party/edge-tts` 含所使用的 LGPL 组件原始 Python 源码；可替换并重新构建。
