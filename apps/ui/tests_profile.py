import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from PIL import Image

User = get_user_model()


class ProfileViewTests(TestCase):
    def setUp(self):
        self.temp_media_root = tempfile.mkdtemp(prefix="campuscalm_test_media_")
        self.override = override_settings(MEDIA_ROOT=self.temp_media_root)
        self.override.enable()

        self.user = User.objects.create_user(
            email="profile-ui@example.com",
            name="Profile UI",
            password="pass12345",
        )
        UserProfile.objects.get_or_create(user=self.user)

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.temp_media_root, ignore_errors=True)

    def test_profile_requires_authentication(self):
        response = self.client.get(reverse("ui-profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_profile_get_returns_200(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("ui-profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meu Perfil")

    def test_profile_post_saves_gender(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("ui-profile"),
            {"gender": UserProfile.GENDER_FEMALE},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("ui-profile"))

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.gender, UserProfile.GENDER_FEMALE)

    def test_profile_post_saves_avatar_upload(self):
        self.client.force_login(self.user)
        image_io = BytesIO()
        image = Image.new("RGB", (1, 1), color="#4f46e5")
        image.save(image_io, format="PNG")
        avatar_file = SimpleUploadedFile("avatar.png", image_io.getvalue(), content_type="image/png")

        response = self.client.post(
            reverse("ui-profile"),
            {"gender": "", "avatar": avatar_file},
        )
        self.assertEqual(response.status_code, 302)

        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(bool(profile.avatar))
        self.assertTrue(profile.avatar.name.startswith("avatars/"))
