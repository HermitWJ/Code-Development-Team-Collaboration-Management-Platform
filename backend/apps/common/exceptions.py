from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class ApiError(Exception):
    """业务异常：统一输出 {code, message, detail}。"""

    def __init__(self, http_status, code, message, detail=None):
        super().__init__(message)
        self.http_status = http_status
        self.code = code
        self.message = message
        self.detail = detail or {}


def api_exception_handler(exc, context):
    if isinstance(exc, ApiError):
        return Response(
            {"code": exc.code, "message": exc.message, "detail": exc.detail},
            status=exc.http_status,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if response.status_code == status.HTTP_400_BAD_REQUEST:
        code, message = "INVALID_PARAM", "请求参数不合法"
    elif response.status_code == status.HTTP_401_UNAUTHORIZED:
        code, message = "UNAUTHENTICATED", "请先登录"
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        code, message = "ROLE_NOT_ALLOWED", "没有权限执行该操作"
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        code, message = "NOT_FOUND", "资源不存在"
    else:
        code, message = "REQUEST_FAILED", "请求失败"

    return Response(
        {"code": code, "message": message, "detail": response.data},
        status=response.status_code,
        headers=response.headers,
    )
