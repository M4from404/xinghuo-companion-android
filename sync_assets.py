"""Copy only release assets; keep the Windows source unchanged."""
from pathlib import Path
import hashlib
import shutil

root = Path(__file__).resolve().parent
source = Path(r'C:\Users\a1331\Desktop\dadike\dadike')
assets = root / 'app/src/main/assets'
web = assets / 'web'
web.mkdir(parents=True, exist_ok=True)
for name in ['character.png', 'app_icon.png', 'video/greet.mp4', 'video/think.mp4',
             'video/interact.mp4', *[f'voice/v0{i}.mp3' for i in range(7)]]:
    target = web / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / name, target)
for name in ['agent.html', 'game.html']:
    html = (source / name).read_text(encoding='utf-8')
    html = html.replace('</head>', '<script src="android-bridge.js"></script>\n<link rel="stylesheet" href="mobile.css">\n</head>')
    html = html.replace('sessionStorage', 'localStorage')
    html = html.replace('请关闭窗口，重新打开“星火同行.exe”。', '请完全关闭星火同行 App 后重新打开。')
    html = html.replace('请重新打开“星火同行.exe”。', '请完全关闭星火同行 App 后重新打开。')
    html = html.replace('Enter 发送 · Shift+Enter 换行', '点击箭头发送 · 语音转文字后可修改')
    if name == 'game.html':
        html = html.replace('<body>', '<body class="game-page">')
        html = html.replace('当前窗口内返回聊天或刷新页面，也可以接着完成未答完的题。', '返回聊天或重新打开 App，也可以接着完成未答完的题。')
    else:
        html = html.replace('<div class="actions"><button onclick="closeServiceInfo()">',
            '<p class="hint">安卓 1.0.0 · 角色资源与题库随 App 安装。语音输入使用手机系统的识别服务；没有识别服务时可使用键盘语音输入。聊天记录和闯关进度保存在本机，卸载会清除。</p>'
            '<p class="hint">在线甜声由 Microsoft Edge 语音服务生成，朗读文本会发送至该服务。<a href="licenses.html">开源组件说明</a></p>'
            '<div class="actions"><button onclick="closeServiceInfo()">')
        html = html.replace("e.error==='not-allowed'?", "e.error==='service-not-allowed'?'手机没有可用的语音识别服务，请使用键盘语音输入或打字。':e.error==='not-allowed'?")
        html = html.replace('已转成文字，检查后按 Enter 或点击发送。', '已转成文字，检查后点击发送。')
    (web / name).write_text(html, encoding='utf-8')
for name in ['android-bridge.js', 'mobile.css']:
    shutil.copy2(root / 'mobile' / name, web / name)
for name in ['static_server.py', 'model_provider.py', 'tts_server.py']:
    text = (source / name).read_text(encoding='utf-8')
    if name == 'static_server.py':
        text = text.replace("'version': '1.2.6'", "'version': '1.0.0-android'")
    (root / 'app/src/main/python' / name).write_text(text, encoding='utf-8')
drawable = root / 'app/src/main/res/drawable'
drawable.mkdir(parents=True, exist_ok=True)
shutil.copy2(source / 'app_icon.png', drawable / 'app_icon.png')
(web / 'licenses.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>开源组件说明</title><style>body{font:16px/1.8 sans-serif;color:#58282a;background:#fff8f0;margin:24px}a{color:#a41932}li{margin:12px 0}</style><h1>开源组件说明</h1><p><a href="agent.html">返回星火同行</a></p><p>星火同行安卓 1.0.0 使用以下开源组件。各组件的版权与许可文件保留在应用和源码包中。</p><ul><li>Python 3.13 · Python Software Foundation License</li><li>Chaquopy 17.0.0 · MIT</li><li>edge-tts 7.2.8 · LGPL-3.0</li><li>aiohttp、multidict、yarl、frozenlist、propcache · Apache-2.0</li><li>certifi · MPL-2.0</li><li>aiohappyeyeballs · PSF-2.0</li><li>aiosignal、attrs、tabulate · MIT</li><li>typing_extensions · PSF-2.0</li></ul><p>在线对话：Pollinations 公共接口。角色、动画和离线题库由项目提供。</p><p><a href="third-party-notices.txt">查看完整第三方许可</a></p></html>''', encoding='utf-8')
notices = []
site = root / 'app/build/python/pip/release/common'
if not site.exists():
    site = root.parent / '.xinghuo-build-env/Lib/site-packages'
for name in ['edge_tts', 'aiohttp', 'multidict', 'yarl', 'frozenlist', 'propcache', 'certifi', 'idna',
             'aiohappyeyeballs', 'aiosignal', 'attrs', 'tabulate', 'typing_extensions']:
    for dist in site.glob(name + '-*.dist-info'):
        for path in dist.rglob('*'):
            if path.is_file() and any(word in path.name.lower() for word in ['licen', 'copying', 'notice']):
                notices.append(f'\n=== {dist.name} / {path.relative_to(dist)} ===\n' + path.read_text(encoding='utf-8', errors='replace'))
(web / 'third-party-notices.txt').write_text(''.join(notices), encoding='utf-8')
digest = hashlib.sha256()
for path in sorted(web.rglob('*')):
    if path.is_file():
        digest.update(path.relative_to(web).as_posix().encode())
        digest.update(path.read_bytes())
(assets / 'web-manifest.sha256').write_text(digest.hexdigest(), encoding='ascii')
print('ANDROID_ASSETS_READY', sum(p.is_file() for p in web.rglob('*')))
