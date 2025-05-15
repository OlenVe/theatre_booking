import json
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from theatre.models import Performance, Ticket, Genre, Actor, Play, TheatreHall
from django.utils.timezone import make_aware
from datetime import datetime

User = get_user_model()


class BookingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123"
        )
        self.genre = Genre.objects.create(name="Drama")
        self.actor = Actor.objects.create(first_name="John", last_name="Wick")
        self.play = Play.objects.create(
            title="Test Play",
            description="Test Description",
            acts=2,
            genre=self.genre,
        )
        self.play.actors.add(self.actor)
        self.theatre_hall = TheatreHall.objects.create(
            name="Red Hall",
            rows=5,
            seats_in_row=20
        )
        self.performance = Performance.objects.create(
            play=self.play,
            theatre_hall=self.theatre_hall,
            show_time=make_aware(datetime(2025, 5, 15, 18, 0, 0))
        )

        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def authenticate(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

    def test_create_single_ticket_booking(self):
        self.authenticate()
        response = self.client.post("/api/theatre/ticket/", {
            "performance": self.performance.id,
            "row": 1,
            "seat": 1
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Ticket.objects.count(), 1)
        self.assertEqual(Ticket.objects.first().performance, self.performance)

    def test_create_bulk_tickets_booking(self):
        self.authenticate()
        data = [
            {"performance": self.performance.id, "row": 2, "seat": 1},
            {"performance": self.performance.id, "row": 2, "seat": 2}
        ]
        response = self.client.post(
            "/api/theatre/ticket/",
                  data=json.dumps(data),
                  content_type="application/json"
        )
        print("RESPONSE DATA:", response.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Ticket.objects.count(), 2)

        tickets = Ticket.objects.all()
        self.assertEqual(tickets[0].reservation, tickets[1].reservation)

    def test_get_performance_list(self):
        response = self.client.get("/api/theatre/performances/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Play")

    def test_jwt_authentication(self):
        # Without token
        response = self.client.get("/api/theatre/performances/")
        self.assertEqual(response.status_code, 200)  # Якщо не захищено, то 200. Якщо захищено — очікуй 401

        # With token
        self.authenticate()
        response = self.client.get("/api/theatre/performances/")
        self.assertEqual(response.status_code, 200)
