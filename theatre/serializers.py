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
            "genre",
            "actors",
        )


class PlayListSerializer(serializers.ModelSerializer):
    genre = serializers.CharField(source="genre.name", read_only=True)
    actors = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="full_name"
    )

    class Meta:
        model = Play
        fields = ("id",
                  "genre",
                  "title",
                  "acts",
                  "actors",
                  "image",
                  )


class PlayDetailSerializer(serializers.ModelSerializer):
    genre = GenreSerializer(read_only=True)
    actors = ActorSerializer(many=True, read_only=True)

    class Meta:
        model = Play
        fields = (
            "id",
            "title",
            "description",
            "acts",
            "genre",
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


class TicketCreateSerializer(serializers.ModelSerializer):
    row = serializers.IntegerField(min_value=1)
    seat = serializers.IntegerField(min_value=1)

    class Meta:
        model = Ticket
        fields = ("row", "seat")


class PerformanceDetailSerializer(PerformanceSerializer):
    play = PlayListSerializer(many=False, read_only=True)
    theatre_hall = TheatreHallSerializer(many=False, read_only=True)
    taken_places = TicketCreateSerializer(
        source="tickets",
        many=True,
        read_only=True
    )

    class Meta:
        model = Performance
        fields = ("id", "show_time", "play", "theatre_hall", "taken_places")


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
    tickets = serializers.SerializerMethodField()

    created_at = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", read_only=True)

    class Meta:
        model = Reservation
        fields = ("id", "tickets", "created_at", "user")
        read_only_fields = ("user",)

    def get_tickets(self, obj):
        return TicketListSerializer(obj.tickets.all(), many=True, context=self.context).data


class ReservationListSerializer(ReservationSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)


class ReservationCreateSerializer(serializers.Serializer):
    performance_id = serializers.IntegerField()
    tickets = TicketCreateSerializer(many=True, allow_empty=False) # allow_empty=False гарантує, що квитки завжди є

    def validate(self, data):
        performance_id = data['performance_id']
        tickets_data = data['tickets']

        try:
            performance = Performance.objects.select_related('theatre_hall').get(id=performance_id)
        except Performance.DoesNotExist:
            raise serializers.ValidationError({"performance_id": "Performance with this ID does not exist."})

        theatre_hall = performance.theatre_hall

        requested_seats_in_request = set()
        for ticket in tickets_data:
            row = ticket['row']
            seat = ticket['seat']

            Ticket.validate_ticket(row, seat, theatre_hall, serializers.ValidationError)

            if (row, seat) in requested_seats_in_request:
                raise serializers.ValidationError(
                    {"tickets": f"Seat {seat} in row {row} is duplicated in your request."}
                )
            requested_seats_in_request.add((row, seat))

        existing_tickets_for_performance = Ticket.objects.filter(
            performance=performance
        ).values_list('row', 'seat')

        taken_seats_in_db = set(existing_tickets_for_performance)

        for ticket_data in tickets_data:
            if (ticket_data['row'], ticket_data['seat']) in taken_seats_in_db:
                raise serializers.ValidationError(
                    {"tickets": f"Seat {ticket_data['seat']} in row {ticket_data['row']} is already taken for this performance."}
                )

        data['performance'] = performance
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        performance = validated_data['performance']
        tickets_data = validated_data['tickets']

        with transaction.atomic():
            reservation = Reservation.objects.create(user=user)
            ticket_objs = [
                Ticket(
                    performance=performance,
                    reservation=reservation,
                    row=ticket['row'],
                    seat=ticket['seat']
                )
                for ticket in tickets_data
            ]
            Ticket.objects.bulk_create(ticket_objs)

        return reservation
