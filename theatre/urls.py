from django.urls import path, include
from rest_framework import routers

from theatre.views import (
    GenreViewSet,
    ActorViewSet,
    TheatreHallViewSet,
    PerformanceViewSet,
    PlaysViewSet,
    ReservationViewSet,
)

app_name = "theatre"

router = routers.DefaultRouter()
router.register("genres", GenreViewSet, basename="genre")
router.register("actors", ActorViewSet, basename="actor")
router.register("theatre_halls", TheatreHallViewSet, basename="theatre_hall")
router.register("performances", PerformanceViewSet, basename="performance")
router.register("plays", PlaysViewSet, basename="play")
router.register("reservations", ReservationViewSet, basename="reservation")

urlpatterns = [path("", include(router.urls))]
