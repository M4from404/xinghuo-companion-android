# -*- coding: utf-8 -*-
"""在线语音合成及本机缓存，由应用同源 HTTP 接口提供。"""
import asyncio
import hashlib
import os
import tempfile
import threading
from contextlib import contextmanager
import edge_tts

CACHE_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')),
                         'XinghuoTongxing', 'voice-cache')
EDGE_VOICES = {
    'fast': ('zh-CN-XiaoyiNeural', '+8%', '+20Hz'),
    'child': ('zh-CN-XiaoxiaoNeural', '+5%', '+45Hz'),
}
_lock_guard = threading.Lock()
_inflight = {}


@contextmanager
def _text_lock(key):
    # Only identical text shares a lock. Unrelated chunks must not wait on a hash collision.
    with _lock_guard:
        entry = _inflight.setdefault(key, [threading.Lock(), 0])
        entry[1] += 1
    try:
        with entry[0]:
            yield
    finally:
        with _lock_guard:
            entry[1] -= 1
            if entry[1] == 0:
                del _inflight[key]


async def _edge_synth(text, engine):
    voice, rate, pitch = EDGE_VOICES[engine]
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    output = bytearray()
    async for chunk in comm.stream():
        if chunk['type'] == 'audio':
            output.extend(chunk['data'])
    if len(output) < 1000:
        raise RuntimeError('在线语音服务没有返回音频')
    return bytes(output)


def synthesize(text, engine='fast'):
    return asyncio.run(asyncio.wait_for(_edge_synth(text, engine), timeout=18))


def get_audio(text, engine='fast'):
    text = text.strip()
    if not text or len(text) > 300:
        raise ValueError('语音文字应为 1 至 300 字')
    if engine not in EDGE_VOICES:
        raise ValueError('不支持该音色')
    key = hashlib.sha256((engine + ':' + text).encode('utf-8')).hexdigest()
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, key + '.mp3')
    with _text_lock(key):
        if os.path.isfile(path) and os.path.getsize(path) >= 1000:
            with open(path, 'rb') as f:
                return f.read()
        audio = synthesize(text, engine)
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(dir=CACHE_DIR, suffix='.tmp', delete=False) as f:
                tmp = f.name
                f.write(audio)
            os.replace(tmp, path)
        finally:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        return audio
