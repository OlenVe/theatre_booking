from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from visitor.views import CreateUserView, ManageUserView, TelegramAuthView

app_name = "visitor"

urlpatterns = [
    path("register", CreateUserView.as_view(), name="create"),
    path("token", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify", TokenVerifyView.as_view(), name="token_verify"),
    path("me", ManageUserView.as_view(), name="manage"),
    path("telegram-auth/", TelegramAuthView.as_view(), name="telegram_auth"),
]
