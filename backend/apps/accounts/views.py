from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import ApiError


def user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.get_full_name() or user.username,
    }


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        user = authenticate(username=username, password=password)
        if user is None:
            raise ApiError(401, "UNAUTHENTICATED", "用户名或密码不正确")
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": user_payload(user)})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(user_payload(request.user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"ok": True})


class UserSearchView(APIView):
    """按用户名或邮箱搜索可添加的人；只回 id 与用户名，不外泄其它字段。"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        keyword = (request.query_params.get("q") or "").strip()
        if len(keyword) < 1:
            return Response([])
        User = get_user_model()
        rows = (
            User.objects.filter(Q(username__icontains=keyword) | Q(email__icontains=keyword))
            .order_by("id")
            .values("id", "username")[:10]
        )
        return Response(
            [{"id": row["id"], "username": row["username"]} for row in rows]
        )
