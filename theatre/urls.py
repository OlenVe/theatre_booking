from django.urls import path, include
from rest_framework import routers

from theatre.views import (
    GenreViewSet,
    ActorViewSet,
    TheatreHallViewSet,
    PerformanceViewSet,
    PlayViewSet,
    ReservationViewSet,
)

app_name = "theatre"

router = routers.DefaultRouter()
router.register("genres", GenreViewSet, basename="genres")
router.register("actors", ActorViewSet, basename="actors")
router.register("theatre_halls", TheatreHallViewSet, basename="theatre_halls")
router.register("performances", PerformanceViewSet, basename="performances")
router.register("plays", PlayViewSet, basename="plays")
router.register("reservations", ReservationViewSet, basename="reservations")

urlpatterns = [path("", include(router.urls))]
