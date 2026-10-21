"""Run the same model/TTS/quiz service entirely inside the Android process."""
import os
import threading
_server = None
_guard = threading.Lock()

def start(web_root, data_root):
    global _server
    with _guard:
        if _server:
            return _server.server_address[1]
        import certifi
        os.environ['SSL_CERT_FILE'] = certifi.where()
        import static_server
        import tts_server
        static_server.ROOT = web_root
        static_server.PROGRESS_FILE = os.path.join(data_root, 'quiz-progress.json')
        static_server.PREFERENCES_FILE = os.path.join(data_root, 'preferences.json')
        tts_server.CACHE_DIR = os.path.join(data_root, 'voice-cache')
        class MobileHandler(static_server.Handler):
            def list_directory(self, path):
                self.send_error(404)
            def do_POST(self):
                if self.path.split('?')[0] == '/api/shutdown':
                    return self._send_json(405, {'error': '请使用手机返回键离开 App'})
                return super().do_POST()
        try:
            _server = static_server.Server(('127.0.0.1', 18766), MobileHandler)
        except OSError:
            _server = static_server.Server(('127.0.0.1', 0), MobileHandler)
        threading.Thread(target=_server.serve_forever, daemon=True, name='xinghuo-http').start()
        return _server.server_address[1]
