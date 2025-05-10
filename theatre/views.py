from django.shortcuts import render
from rest_framework import permissions

from theatre.models import Genre


# Create your views here.
class GenreViewSet:
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


class ActorViewSet:
    pass


class TheatreHallViewSet:
    pass


class PerformanceViewSet:
    pass


class PlaysViewSet:
    pass


class ReservationViewSet:
    pass