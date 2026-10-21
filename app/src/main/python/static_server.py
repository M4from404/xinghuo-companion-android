# -*- coding: utf-8 -*-
"""本地页面、免费在线对话、语音及学习进度服务。"""
import http.server
import json
import os
import re
import socketserver
import sys
import threading
from urllib.parse import urlparse, parse_qs
import tts_server
from model_provider import chat as _chat, service_info, ChatError

ROOT = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')),
                             'XinghuoTongxing', 'quiz-progress.json')
PREFERENCES_FILE = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')),
                                'XinghuoTongxing', 'preferences.json')
_save_lock = threading.RLock()
shutdown_requested = None


def _atomic_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, path)


def _progress(data=None):
    with _save_lock:
        try:
            with open(PROGRESS_FILE, encoding='utf-8') as f:
                old = json.load(f)
        except (OSError, ValueError):
            old = {}
        if not isinstance(old, dict):
            old = {}
        old_cleared = old.get('cleared', [])
        if not isinstance(old_cleared, list):
            old_cleared = []
        cleared = {n for n in old_cleared if type(n) is int and 0 <= n <= 2}
        if data is not None:
            if not isinstance(data.get('cleared', []), list):
                raise ValueError('关卡进度格式无效')
            cleared.update(n for n in data.get('cleared', []) if type(n) is int and 0 <= n <= 2)
        unlocked = 0
        while unlocked in cleared and unlocked < 2:
            unlocked += 1
        result = {'unlocked': unlocked, 'cleared': sorted(cleared)}
        if data is not None:
            _atomic_json(PROGRESS_FILE, result)
        return result


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def _preferences(data=None):
    defaults = {'voiceOn': True, 'engine': 'fast', 'fallbackVoice': ''}
    def valid(key, value):
        if key == 'voiceOn':
            return type(value) is bool
        if key == 'engine':
            return value in ('fast', 'child')
        return isinstance(value, str) and len(value) <= 160
    with _save_lock:
        try:
            with open(PREFERENCES_FILE, encoding='utf-8') as f:
                saved = json.load(f)
        except (OSError, ValueError):
            saved = {}
        result = dict(defaults)
        if isinstance(saved, dict):
            result.update({key: saved[key] for key in defaults if key in saved and valid(key, saved[key])})
        if data is not None:
            for key in defaults:
                if key in data:
                    if not valid(key, data[key]):
                        raise ValueError('声音设置格式无效')
                    result[key] = data[key]
            _atomic_json(PREFERENCES_FILE, result)
        return result


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == '/api/health':
            return self._send_json(200, {'app': 'XinghuoTongxing', 'version': '1.0.0-android', 'ok': True})
        if parsed.path == '/ping':
            return self._send_json(200, {'ok': True})
        if parsed.path == '/tts':
            try:
                audio = tts_server.get_audio(query.get('text', [''])[0], query.get('engine', ['fast'])[0])
            except ValueError as e:
                return self._send_json(400, {'error': str(e)})
            except Exception:
                return self._send_json(503, {'error': '在线语音暂不可用，请使用备用音色'})
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Content-Length', str(len(audio)))
            self.end_headers()
            try:
                self.wfile.write(audio)
            except OSError:
                pass
            return
        if parsed.path == '/api/progress':
            return self._send_json(200, _progress())
        if parsed.path == '/api/preferences':
            return self._send_json(200, _preferences())
        if parsed.path == '/api/config':
            return self._send_json(200, service_info())
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().do_GET()
        size = os.path.getsize(path)
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", rng.strip())
        if not match or not any(match.groups()):
            return super().do_GET()
        if match.group(1):
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else size - 1
        else:
            start = max(0, size - int(match.group(2)))
            end = size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", "bytes */%d" % size)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            self.wfile.write(f.read(end - start + 1))

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host', ''):
                return self._send_json(403, {'error': '请在星火同行窗口内操作'})
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 128 * 1024:
                return self._send_json(400, {"error": "请求内容长度无效"})
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError('请求应为 JSON 对象')
            if path == '/api/progress':
                return self._send_json(200, _progress(data))
            if path == '/api/preferences':
                return self._send_json(200, _preferences(data))
            if path == '/api/config':
                return self._send_json(405, {'error': '免费在线对话无需配置密钥'})
            if path == "/api/chat":
                if data.get('stream') is True:
                    return self._stream_chat(data.get('messages', []))
                return self._send_json(200, {"content": _chat(data.get("messages", []))})
            if path == "/api/shutdown":
                self._send_json(200, {"ok": True})
                if shutdown_requested is not None:
                    shutdown_requested.set()
                return
            return self._send_json(404, {"error": "找不到该接口"})
        except ChatError as e:
            return self._send_json(e.status, {'error': str(e)})
        except (ValueError, json.JSONDecodeError) as e:
            return self._send_json(400, {"error": str(e) or "请求格式无效"})
        except Exception as e:
            return self._send_json(502, {"error": str(e) or "服务请求失败"})

    def _stream_chat(self, messages):
        # Flush each piece immediately; close-delimited NDJSON also works with HTTP/1.0.
        self.send_response(200)
        self.send_header('Content-Type', 'application/x-ndjson; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True

        def emit(value):
            self.wfile.write(_json_bytes(value) + b'\n')
            self.wfile.flush()

        try:
            _chat(messages, on_delta=lambda text: emit({'type': 'delta', 'text': text}))
            emit({'type': 'done'})
        except OSError:
            pass  # Window closed or client cancelled; model semaphore is released by chat().
        except (ChatError, ValueError) as exc:
            try:
                emit({'type': 'error', 'error': str(exc)})
            except OSError:
                pass
        except Exception:
            try:
                emit({'type': 'error', 'error': '回复连接中断，请稍后重试。'})
            except OSError:
                pass

    def _send_json(self, code, value):
        body = _json_bytes(value)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:
            pass

    def log_message(self, *args):
        pass


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def server_bind(self):
        import socket
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
    Server(("127.0.0.1", port), Handler).serve_forever()
