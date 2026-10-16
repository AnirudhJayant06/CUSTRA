"""Bound multipart request bodies before the framework parses them."""

from starlette.responses import JSONResponse


class UploadLimitMiddleware:
    def __init__(self, app, max_bytes: int = 5_050_000):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or not scope["path"].endswith("/documents"):
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = 0
        messages = []
        size = 0
        too_large = declared > self.max_bytes
        while not too_large:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.max_bytes:
                too_large = True
                break
            messages.append(message)
            if not message.get("more_body", False):
                break
        if too_large:
            response = JSONResponse(status_code=413, content={
                "code": "upload_too_large", "message": "Upload one file of at most 5,000,000 bytes", "retryable": False,
            }, headers={"Cache-Control": "private, no-store"})
            return await response(scope, receive, send)
        index = 0
        async def replay():
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return await receive()
        return await self.app(scope, replay, send)
