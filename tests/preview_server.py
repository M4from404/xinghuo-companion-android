from pathlib import Path
import sys, tempfile, threading
root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root/'app/src/main/python'), str(root/'app/build/python/pip/release/common')]
import mobile_server
port = mobile_server.start(str(root/'app/src/main/assets/web'), tempfile.mkdtemp(prefix='xinghuo-android-test-'))
print('MOBILE_TEST_PORT='+str(port), flush=True)
threading.Event().wait()
