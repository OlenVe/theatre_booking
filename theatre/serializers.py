from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from theatre.models import (Genre,
                            Actor,
                            TheatreHall,
                            Play,
                            Performance,
                            Ticket,
                            Reservation
                            )


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name")


class ActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = ("id", "first_name", "last_name", "full_name")


class TheatreHallSerializer(serializers.ModelSerializer):
    class Meta:
        model = TheatreHall
        fields = ("id", "name", "rows", "seats_in_row", "capacity")


class PlaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Play
        fields = (
            "id",
            "title",
            "description",
            "acts",
            "genres",
            "actors",
        )


class PlayListSerializer(serializers.ModelSerializer):
    genres = serializers.CharField(source="genre.name", read_only=True)
    actors = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="full_name"
    )

    class Meta:
        model = Play
        fields = ("id",
                  "genres",
                  "title",
                  "acts",
                  "actors",
                  "image",
                  )


class PlayDetailSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    actors = ActorSerializer(many=True, read_only=True)

    class Meta:
        model = Play
        fields = (
            "id",
            "title",
            "description",
            "acts",
            "genres",
            "actors",
            "image",
        )


class PlayImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Play
        fields = ("id", "image")


class PerformanceSerializer(serializers.ModelSerializer):
    show_time = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", read_only=True)

    class Meta:
        model = Performance
        fields = ("id", "show_time", "play", "theatre_hall")


class PerformanceListSerializer(PerformanceSerializer):
    play_title = serializers.CharField(source="play.title", read_only=True)
    play_genre_name = serializers.CharField(source="play.genre.name", read_only=True)
    play_image = serializers.ImageField(source="play.image", read_only=True)
    theatre_hall_name = serializers.CharField(
        source="theatre_hall.name",
        read_only=True
    )
    theatre_hall_capacity = serializers.IntegerField(
        source="theatre_hall.capacity", read_only=True
    )
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Performance
        fields = (
            "id",
            "show_time",
            "play_title",
            "play_genre_name",
            "play_image",
            "theatre_hall_name",
            "theatre_hall_capacity",
            "tickets_available",
        )


class TicketSeatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("row", "seat")


class PerformanceDetailSerializer(PerformanceSerializer):
    play = PlayListSerializer(many=False, read_only=True)
    theatre_hall = TheatreHallSerializer(many=False, read_only=True)
    taken_places = TicketSeatsSerializer(
        source="tickets",
        many=True,
        read_only=True
    )

    class Meta:
        model = Performance
        fields = ("id", "show_time", "play", "theatre_hall", "taken_places")


class TicketSerializer(serializers.ModelSerializer):
    performance_title = serializers.CharField(write_only=True)
    performance_time = serializers.DateTimeField(write_only=True)
    # reservation = serializers.BooleanField(write_only=True, default=False)
    performance = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = (
            "id",
            "performance_title",
            "performance_time",
            "row",
            "seat",
            # "reservation",
            "performance",
        )
        # read_only_fields = ("id", "reservation")
        read_only_fields = ("id", )

    def validate(self, data):
        performance_title = data.get("performance_title")
        performance_time = data.get("performance_time")

        performance = Performance.objects.filter(
            play__title=performance_title, show_time=performance_time
        )

        if not performance.exists():
            raise serializers.ValidationError(
                {
                    "performance": "Wrong title or time"
                }
            )
        if performance.count() > 1:
            raise serializers.ValidationError(
                {
                    "performance": "Only one time."
                }
            )

        data["performance"] = performance.first()
        return data

    def get_performance(self, obj):
        performance_serializer = PerformanceSerializer(
            instance=obj.performance, context=self.context
        )
        return performance_serializer.data

    def create(self, validated_data):
        validated_data.pop("performance_title")
        validated_data.pop("performance_time")

        # reservation_flag = validated_data.pop("reservation", False)
        performance = validated_data.pop("performance")

        with transaction.atomic():
            # reservation = None
            # if reservation_flag:
            user = self.context["request"].user
            reservation = Reservation.objects.create(user=user)
            validated_data.pop("reservation", None)

            ticket = Ticket.objects.create(
                performance=performance,
                reservation=reservation,
                **validated_data
            )


        return ticket


class TicketListSerializer(serializers.ModelSerializer):
    performance = serializers.CharField(
        source="performance.play.title", read_only=True
    )
    reservation = serializers.CharField(source="reservation.user", read_only=True)
    show_time = serializers.CharField(source="performance.show_time")

    class Meta:
        model = Ticket
        fields = (
            "id",
            "performance",
            "row",
            "seat",
            "reservation",
            "show_time",
        )


class TicketDetailSerializer(serializers.ModelSerializer):
    performance = PerformanceDetailSerializer()
    reservation = serializers.CharField(source="reservation.user", read_only=True)
    show_time = serializers.CharField(source="performance.show_time")

    class Meta:
        model = Ticket
        fields = (
            "id",
            "performance",
            "row",
            "seat",
            "reservation",
            "show_time",
        )


class ReservationSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)
    created_at = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", read_only=True)

    class Meta:
        model = Reservation
        fields = ("id", "tickets", "created_at")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            reservation = Reservation.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(reservation=reservation, **ticket_data)
            return reservation


class ReservationListSerializer(ReservationSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)


class ReservationCreateSerializer(serializers.ModelSerializer):
    tickets = TicketSeatsSerializer(many=True)

    class Meta:
        model = Reservation
        fields = (
            "id",
            "tickets",
            "user",
            "created_at",
        )

    def get_tickets(self, obj):
        tickets = obj.tickets.all()
        return [ticket.show_session.astronomy_show.title for ticket in tickets]


class TicketBulkCreateSerializer(serializers.Serializer):
    tickets = TicketSeatsSerializer(many=True)
    performance_title = serializers.CharField()
    performance_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    def validate(self, attrs):
        title = attrs["performance_title"]
        time = attrs["performance_time"]

        performances = Performance.objects.filter(
            play__title=title, show_time=time
        )
        if not performances.exists():
            raise serializers.ValidationError("Wrong time")
        if performances.count() > 1:
            raise serializers.ValidationError("Chose only 1 performance")
        attrs["performance"] = performances.first()
        return attrs

    def create(self, validated_data):
        performance = validated_data["performance"]
        tickets_data = validated_data["tickets"]
        user = self.context["request"].user

        with transaction.atomic():
            reservation = Reservation.objects.create(user=user)
            tickets = [
                Ticket(
                    performance=performance,
                    reservation=reservation,
                    row=ticket["row"],
                    seat=ticket["seat"]
                )
                for ticket in tickets_data
            ]
            Ticket.objects.bulk_create(tickets)

        return reservation
