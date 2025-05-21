import json
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from theatre.models import Performance, Ticket, Genre, Actor, Play, TheatreHall, Reservation
from django.utils.timezone import make_aware
from datetime import datetime
from unittest.mock import patch

User = get_user_model()


class BookingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpassword"
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

        refresh_admin = RefreshToken.for_user(self.admin_user)
        self.admin_access_token = str(refresh_admin.access_token)

    def authenticate(self, user_type="user"):
        if user_type == "user":
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        elif user_type == "admin":
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_access_token}")
        else:
            self.client.credentials()

    def test_create_reservation_with_single_ticket(self):
        """
        Тестує створення резервації з ОДНИМ квитком через ReservationViewSet.
        """
        self.authenticate()
        initial_ticket_count = Ticket.objects.count()
        initial_reservation_count = Reservation.objects.count()

        data = {
            "performance_id": self.performance.id,
            "tickets": [
                {"row": 1, "seat": 1}
            ]
        }
        response = self.client.post("/api/theatre/reservations/", data, format="json")
        print("RESPONSE DATA (single ticket reservation create):", response.data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Ticket.objects.count(), initial_ticket_count + 1)
        self.assertEqual(Reservation.objects.count(), initial_reservation_count + 1)

        reservation = Reservation.objects.last()
        self.assertEqual(reservation.user, self.user)
        self.assertEqual(reservation.tickets.count(), 1)
        self.assertEqual(reservation.tickets.first().row, 1)
        self.assertEqual(reservation.tickets.first().seat, 1)

    def test_create_reservation_with_multiple_tickets(self):
        """
        Тестує створення резервації з КІЛЬКОМА квитками через ReservationViewSet.
        """
        self.authenticate()
        initial_ticket_count = Ticket.objects.count()
        initial_reservation_count = Reservation.objects.count()

        data = {
            "performance_id": self.performance.id,
            "tickets": [
                {"row": 2, "seat": 1},
                {"row": 2, "seat": 2},
                {"row": 3, "seat": 5}
            ]
        }
        response = self.client.post("/api/theatre/reservations/", data, format="json")
        print("RESPONSE DATA (multiple tickets reservation create):", response.data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Ticket.objects.count(), initial_ticket_count + 3)
        self.assertEqual(Reservation.objects.count(), initial_reservation_count + 1)

        reservation = Reservation.objects.last()
        self.assertEqual(reservation.user, self.user)
        self.assertEqual(reservation.tickets.count(), 3)


        for ticket_data in data["tickets"]:
            self.assertTrue(
                reservation.tickets.filter(
                    performance=self.performance,
                    row=ticket_data["row"],
                    seat=ticket_data["seat"]
                ).exists()
            )

    def test_reservation_duplicate_seat_in_request_fails(self):
        """
        Тестує, що створення резервації не проходить, якщо є дублікат місця в одному запиті.
        """
        self.authenticate()
        data = {
            "performance_id": self.performance.id,
            "tickets": [
                {"row": 1, "seat": 1},
                {"row": 1, "seat": 1},  # Дублікат
            ]
        }
        response = self.client.post("/api/theatre/reservations/", data, format="json")
        print("RESPONSE DATA (duplicate seat in request):", response.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Seat 1 in row 1 is duplicated in your request.", json.dumps(response.data))

    def test_reservation_seat_already_taken_by_another_reservation_fails(self):
        """
        Тестує, що не можна забронювати місце, вже зайняте іншою резервацією.
        """
        self.authenticate()
        # Займаємо одне місце через нову резервацію
        other_user = User.objects.create_user(email="other@example.com", password="password")
        other_reservation = Reservation.objects.create(user=other_user)
        Ticket.objects.create(
            performance=self.performance,
            row=4,
            seat=5,
            reservation=other_reservation
        )


        data = {
            "performance_id": self.performance.id,
            "tickets": [
                {"row": 4, "seat": 5},  # Зайняте місце
                {"row": 4, "seat": 6},
            ]
        }
        response = self.client.post("/api/theatre/reservations/", data, format="json")
        print("RESPONSE DATA (seat taken by another reservation):", response.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already taken for this performance", json.dumps(response.data))

    def test_reservation_invalid_seat_number_fails(self):
        """
        Тестує валідацію місць (вихід за межі) при створенні резервації.
        """
        self.authenticate()
        # Місце занадто велике
        data = {
            "performance_id": self.performance.id,
            "tickets": [
                {"row": 1, "seat": self.theatre_hall.seats_in_row + 1},
            ]
        }
        response = self.client.post("/api/theatre/reservations/", data, format="json")
        print("RESPONSE DATA (invalid seat number):", response.data)
        self.assertEqual(response.status_code, 400)
        # self.assertIn(f"Seat {self.theatre_hall.seats_in_row + 1} is out of range (1, {self.theatre_hall.seats_in_row})",
        #               json.dumps(response.data))


        data = {
            "performance_id": self.performance.id,
            "tickets": [
                {"row": self.theatre_hall.rows + 1, "seat": 1},
            ]
        }
        response = self.client.post("/api/theatre/reservations/", data, format="json")
        print("RESPONSE DATA (invalid row number):", response.data)
        self.assertEqual(response.status_code, 400)
        # self.assertIn(f"Row {self.theatre_hall.rows + 1} is out of range (1-{self.theatre_hall.rows})",
        #               json.dumps(response.data))


        data = {
            "performance_id": self.performance.id,
            "tickets": [
                {"row": 1, "seat": 0},
            ]
        }
        response = self.client.post("/api/theatre/reservations/", data, format="json")
        print("RESPONSE DATA (seat less than 1):", response.data)
        self.assertEqual(response.status_code, 400)
        # self.assertIn("min_value", json.dumps(response.data))

    def test_create_reservation_without_tickets_fails(self):
        """
        Тестує, що не можна створити резервацію без квитків (allow_empty=False).
        """
        self.authenticate()
        data = {
            "performance_id": self.performance.id,
            "tickets": []
        }
        response = self.client.post("/api/theatre/reservations/", data, format="json")
        print("RESPONSE DATA (empty tickets):", response.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("This list may not be empty.", json.dumps(response.data))

    def test_get_performance_list(self):
        """
        Тестує отримання списку вистав.
        """
        response = self.client.get("/api/theatre/performances/")
        print("PERFORMANCE LIST RESPONSE DATA:", response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["play_title"], "Test Play")

    def test_jwt_authentication_for_public_and_protected_endpoints(self):
        """
        Тестує JWT аутентифікацію для захищених та публічних (read-only) ендпоінтів.
        """
        self.client.credentials()  # Без токена
        response = self.client.get("/api/theatre/performances/")
        self.assertEqual(response.status_code, 200)

        self.authenticate(user_type="user")
        response = self.client.get("/api/theatre/performances/")
        self.assertEqual(response.status_code, 200)

        self.client.credentials()
        response = self.client.get("/api/theatre/reservations/")
        self.assertEqual(response.status_code, 401)

        self.authenticate(user_type="user")
        response = self.client.get("/api/theatre/reservations/")
        self.assertEqual(response.status_code, 200)

    def test_admin_can_create_genre(self):
        """
        Тестує, що адмін може створити новий жанр.
        """
        self.authenticate(user_type="admin")
        data = {"name": "Comedy"}
        response = self.client.post("/api/theatre/genres/", data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Genre.objects.count(), 2)

    def test_regular_user_cannot_create_genre(self):
        """
        Тестує, що звичайний користувач не може створити новий жанр.
        """
        self.authenticate(user_type="user")
        data = {"name": "Thriller"}
        response = self.client.post("/api/theatre/genres/", data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Genre.objects.count(), 1)

    @patch('PIL.Image.open')
    def test_admin_can_upload_play_image(self, mock_image_open):
        """
        Тестує, що адмін може завантажити зображення для вистави.
        """
        self.authenticate(user_type="admin")
        from PIL import Image
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile

        mock_image_open.return_value.__enter__.return_value = Image.new('RGB', (100, 100))

        image = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)

        image_file = SimpleUploadedFile("test_image.jpg", buffer.getvalue(), content_type="image/jpeg")

        response = self.client.post(
            f"/api/theatre/plays/{self.play.id}/upload-image/",
            {"image": image_file},
            format="multipart"
        )
        print("UPLOAD IMAGE RESPONSE DATA:", response.data)
        self.assertEqual(response.status_code, 200)
        self.play.refresh_from_db()
        self.assertIsNotNone(self.play.image)
        self.assertIn("image", response.data)

    def test_user_cannot_upload_play_image(self):
        """
        Тестує, що звичайний користувач не може завантажити зображення для вистави.
        """
        self.authenticate(user_type="user")
        data = {"image": "dummy_image_data"}
        response = self.client.post(
            f"/api/theatre/plays/{self.play.id}/upload-image/",
            data,
            format="multipart"
        )
        self.assertEqual(response.status_code, 403)