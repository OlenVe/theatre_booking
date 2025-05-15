from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.exceptions import ValidationError as DFRValidationError

from theatre.models import TheatreHall, Play, Performance, Reservation, Ticket
from django.contrib.auth import get_user_model
from django.utils import timezone


class TheatreHallModelTest(TestCase):
    def test_capacity_property(self):
        hall = TheatreHall.objects.create(name="Main Hall", rows=10, seats_in_row=20)
        self.assertEqual(hall.capacity, 200)


class TicketModelValidationTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpass"
        )
        self.hall = TheatreHall.objects.create(name="Test Hall", rows=5, seats_in_row=10)
        self.play = Play.objects.create(title="Наталка Полтавка", description="Драма", acts=3)
        self.performance = Performance.objects.create(
            play=self.play,
            theatre_hall=self.hall,
            show_time=timezone.now()
        )
        self.reservation = Reservation.objects.create(user=self.user)

    def test_invalid_row_raises_validation_error(self):
        ticket = Ticket(
            performance=self.performance,
            reservation=self.reservation,
            row=6,
            seat=5
        )

        with self.assertRaises(DFRValidationError):
            ticket.full_clean()

    def test_ticket_unique_constraint(self):
        Ticket.objects.create(
            performance=self.performance,
            reservation=self.reservation,
            row=1,
            seat=1
        )


        duplicate_ticket = Ticket(
            performance=self.performance,
            reservation=self.reservation,
            row=1,
            seat=1
        )

        with self.assertRaises(ValidationError):
            duplicate_ticket.full_clean()