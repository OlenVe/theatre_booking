from datetime import datetime

from django.db.models import F, Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from theatre.models import Genre, Actor, TheatreHall, Play, Reservation, Performance, Ticket
from theatre.permissions import IsAdminOrReadOnly
from theatre.serializers import (
    GenreSerializer,
    ActorSerializer,
    TheatreHallSerializer,
    PlaySerializer,
    PlayListSerializer,
    PlayDetailSerializer,
    PlayImageSerializer,
    ReservationSerializer,
    ReservationListSerializer,
    TicketSeatsSerializer,
    PerformanceSerializer,
    PerformanceListSerializer,
    PerformanceDetailSerializer,
    TicketSerializer,
    TicketListSerializer,
    TicketDetailSerializer,
    ReservationCreateSerializer, TicketBulkCreateSerializer
)


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrReadOnly,)


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrReadOnly,)


class TheatreHallViewSet(viewsets.ModelViewSet):
    queryset = TheatreHall.objects.all()
    serializer_class = TheatreHallSerializer
    permission_classes = (IsAdminOrReadOnly,)


class PerformancePagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class PerformanceViewSet(viewsets.ModelViewSet):
    queryset = (
        Performance.objects.all()
        .select_related("theatre_hall", "play")
        .annotate(
            tickets_available=(
                F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                - Count("tickets")
            )
        )
    )
    serializer_class = PerformanceSerializer
    pagination_class = PerformancePagination
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self):
        date = self.request.query_params.get("date")
        play_id_str = self.request.query_params.get("play")

        queryset = self.queryset

        if date:
            date = datetime.strptime(date, "%Y-%m-%d").date()
            queryset = queryset.filter(show_time__date=date)

        if play_id_str:
            queryset = queryset.filter(movie_id=int(play_id_str))

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PerformanceListSerializer

        if self.action == "retrieve":
            return PerformanceDetailSerializer

        return PerformanceSerializer


class PlayViewSet(viewsets.ModelViewSet):
    queryset = Play.objects.prefetch_related("actors").select_related("genre")
    serializer_class = PlaySerializer
    permission_classes = (IsAdminOrReadOnly,)

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        """Retrieve the movies with filters"""
        title = self.request.query_params.get("title")
        genres = self.request.query_params.get("genres")
        actors = self.request.query_params.get("actors")

        queryset = self.queryset

        if title:
            queryset = queryset.filter(title__icontains=title)

        if genres:
            genres_ids = self._params_to_ints(genres)
            queryset = queryset.filter(genres__id__in=genres_ids)

        if actors:
            actors_ids = self._params_to_ints(actors)
            queryset = queryset.filter(actors__id__in=actors_ids)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return PlayListSerializer

        if self.action == "retrieve":
            return PlayDetailSerializer

        if self.action == "upload_image":
            return PlayImageSerializer

        return PlaySerializer

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading image to specific play"""
        play = self.get_object()
        serializer = self.get_serializer(play, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReservationPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.prefetch_related(
        "tickets__performance__play", "tickets__performance__theatre_hall"
    )
    serializer_class = ReservationSerializer
    pagination_class = ReservationPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user)


    def get_serializer_class(self):
        serializer_class = self.serializer_class

        if self.action == "list":
            serializer_class =  ReservationListSerializer
        if self.action == "create":
            serializer_class = ReservationCreateSerializer

        return serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset
        queryset = queryset.select_related("performance", "reservation")
        title = self.request.query_params.get("title")

        if title:
            queryset = queryset.filter(performance__play__title=title)

        return queryset

    def get_serializer_class(self):
        serializer_class = self.serializer_class

        if self.action == "list":
            serializer_class = TicketListSerializer

        if self.action == "create":
            serializer_class = TicketSerializer

        if self.action == "retrieve":
            serializer_class = TicketDetailSerializer

        return serializer_class

    def perform_create(self, serializer):
        user = self.request.user
        reservation = Reservation.objects.create(user=user)
        serializer.save(reservation=reservation)

    @action(
        methods=["POST"],
        detail=False,
        url_path="bulk-create",
        permission_classes=[IsAuthenticated]
    )
    def bulk_create(self, request):

        tickets_data = request.data
        user = self.request.user

        reservation = Reservation.objects.create(user=user)

        for ticket_data in tickets_data:
            ticket_data["reservation"] = reservation.id

        serializer = TicketBulkCreateSerializer(data=tickets_data, many=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(ReservationSerializer(reservation).data, status=status.HTTP_201_CREATED)