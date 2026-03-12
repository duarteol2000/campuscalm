from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User


class AuthTests(APITestCase):
    def test_register_and_login(self):
        register_url = "/api/auth/register/"
        payload = {
            "email": "test@example.com",
            "name": "Teste",
            "password": "strongpass123",
        }
        response = self.client.post(register_url, payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)

        login_url = "/api/auth/login/"
        login_response = self.client.post(login_url, {"email": payload["email"], "password": payload["password"]})
        self.assertEqual(login_response.status_code, 200)
        self.assertIn("access", login_response.data)

    def test_register_rejects_role_and_institution_override(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "elevate@example.com",
                "name": "Elevate",
                "password": "strongpass123",
                "role": User.ROLE_INSTITUTION_ADMIN,
                "institution": 999,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
