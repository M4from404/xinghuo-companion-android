# -*- coding: utf-8 -*-
"""Pollinations 旧版匿名文字接口：不读取、保存或发送用户密钥。"""
import json
import re
import socket
import threading
import urllib.error
import urllib.request

ENDPOINT = 'https://text.pollinations.ai/openai'
MODEL = 'openai'  # 官方旧接口的别名；2026-10-05 实测返回 gpt-oss-20b。
TIMEOUT = 60
_inflight = threading.BoundedSemaphore(1)


class ChatError(RuntimeError):
    def __init__(self, message, status=503):
        super().__init__(message)
        self.status = status


def service_info():
    return {'provider': 'pollinations', 'name': 'Pollinations 免费在线对话',
            'model': MODEL, 'requiresKey': False, 'version': '1.2.6'}


class _VisibleText:
    """Incrementally discard thinking tags, including tags split across SSE events."""
    def __init__(self):
        self.pending = ''
        self.hidden = False

    def feed(self, text):
        self.pending += text
        visible = []
        while self.pending:
            token = '</think>' if self.hidden else '<think>'
            index = self.pending.lower().find(token)
            if index >= 0:
                if not self.hidden:
                    visible.append(self.pending[:index])
                self.pending = self.pending[index + len(token):]
                self.hidden = not self.hidden
                continue
            keep = 0
            for length in range(1, len(token)):
                if self.pending.lower().endswith(token[:length]):
                    keep = length
            if not self.hidden:
                visible.append(self.pending[:-keep] if keep else self.pending)
            self.pending = self.pending[-keep:] if keep else ''
            break
        return ''.join(visible)

    def finish(self):
        if self.hidden or self.pending:
            raise ChatError('这次回复未完整生成，请重新发送。')


def _read_stream(response, on_delta):
    visible = _VisibleText()
    parts, event_lines = [], []
    total = 0
    completed = False
    done_marker = False

    def event(raw):
        nonlocal completed, done_marker
        if raw == '[DONE]':
            completed = done_marker = True
            return
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get('error'):
            raise ChatError('免费服务暂时未能完成回复，请稍后重试。')
        for choice in data.get('choices', []):
            if not isinstance(choice, dict):
                continue
            delta = choice.get('delta') or {}
            text = delta.get('content') if isinstance(delta, dict) else None
            if isinstance(text, str) and text:
                cleaned = visible.feed(text)
                if cleaned:
                    parts.append(cleaned)
                    on_delta(cleaned)
            if choice.get('finish_reason') is not None:
                completed = True

    for raw in response:
        total += len(raw)
        if total > 1024 * 1024:
            raise ChatError('免费服务返回的内容过长，请稍后重试。')
        line = raw.decode('utf-8').rstrip('\r\n')
        if not line:
            if event_lines:
                event('\n'.join(event_lines))
                event_lines = []
                if done_marker:
                    break
        elif line.startswith('data:'):
            event_lines.append(line[5:].lstrip(' '))
    if event_lines:
        event('\n'.join(event_lines))
    visible.finish()
    if not completed:
        raise ChatError('连接中断，本条回复未完整生成，请重新发送。')
    content = ''.join(parts).strip()
    if not content:
        raise ChatError('免费服务暂时没有返回正文，请稍后再试。')
    return content


def chat(messages, on_delta=None):
    if not isinstance(messages, list):
        raise ValueError('对话内容格式无效')
    clean = []
    items = messages if len(messages) <= 32 else messages[:1] + messages[-31:]
    for item in items:
        if not isinstance(item, dict) or item.get('role') not in ('system', 'user', 'assistant'):
            continue
        content = item.get('content')
        if isinstance(content, str) and content.strip() and len(content) <= 6000:
            clean.append({'role': item['role'], 'content': content})
    if not clean or not any(m['role'] == 'user' for m in clean):
        raise ValueError('请先输入想聊的内容')
    if not _inflight.acquire(blocking=False):
        raise ChatError('上一条回复还在生成，请稍等片刻再发送。', 429)
    try:
        payload = json.dumps({'model': MODEL, 'messages': clean, 'stream': on_delta is not None,
            'reasoning_effort': 'low', 'max_tokens': 900}, ensure_ascii=False).encode('utf-8')
        request = urllib.request.Request(ENDPOINT, data=payload, method='POST', headers={
            'Content-Type': 'application/json', 'Accept': 'text/event-stream' if on_delta else 'application/json',
            'User-Agent': 'XinghuoTongxing/1.2.6'})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            if on_delta and 'text/event-stream' in response.headers.get('Content-Type', ''):
                return _read_stream(response, on_delta)
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ChatError('免费服务返回的内容过长，请稍后重试。')
        data = json.loads(raw.decode('utf-8'))
        choices = data.get('choices') if isinstance(data, dict) else None
        first = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
        message = first.get('message')
        content = message.get('content') if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ChatError('免费服务暂时没有返回正文，请稍后再试。')
        # 不把模型的思考字段或意外返回的思考标签展示、朗读给用户。
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.S | re.I).strip()
        if not content or re.search(r'<think>', content, re.I):
            raise ChatError('这次回复未完整生成，请重新发送。')
        if on_delta:
            on_delta(content)
        return content
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        if code == 429:
            raise ChatError('免费服务当前请求较多，请稍后重试；角色互动和思政闯关仍可使用。', 429) from None
        if code in (401, 402, 403, 404, 410):
            raise ChatError('免 Key 对话入口暂不可用，可能是平台访问规则发生变化。请稍后再试。') from None
        raise ChatError('免费对话服务暂时繁忙（HTTP %d），请稍后重试。' % code) from None
    except (TimeoutError, socket.timeout):
        raise ChatError('等待回复超时，免费服务可能正在排队，请稍后重试。', 504) from None
    except urllib.error.URLError:
        raise ChatError('无法连接在线对话服务，请检查网络后重试。') from None
    except (ValueError, UnicodeError):
        raise ChatError('免费服务返回格式异常，请稍后重试。') from None
    finally:
        _inflight.release()
