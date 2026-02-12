from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from brain.models import CategoriaEmocional, GatilhoEmocional, InteracaoAluno, MicroIntervencao, RespostaEmocional

User = get_user_model()


class WidgetChatTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="brain@example.com", name="Brain", password="pass12345")
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        self.multi_categoria = CategoriaEmocional.objects.create(nome="Multipla", slug="multipla_teste", emoji="🙂")
        GatilhoEmocional.objects.create(categoria=self.multi_categoria, palavras_chave="zzmulti")
        RespostaEmocional.objects.create(categoria=self.multi_categoria, texto="Resposta A")
        RespostaEmocional.objects.create(categoria=self.multi_categoria, texto="Resposta B")
        RespostaEmocional.objects.create(categoria=self.multi_categoria, texto="Resposta C")

        # Seed inicial deve manter ao menos 2 microintervencoes ativas.
        self.assertGreaterEqual(MicroIntervencao.objects.filter(ativo=True).count(), 2)

    def test_detects_social_category(self):
        response = self.client.post("/api/widget/chat/", {"message": "Tenho muita GRATIDAO pela ajuda!"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "social")
        self.assertEqual(response.data["emoji"], "🙌")
        self.assertIn(
            response.data["reply"],
            {
                "Fico feliz em ajudar 😊",
                "Sempre que precisar, estou aqui.",
                "Conta comigo para o que precisar.",
                "É muito bom saber que estou ajudando.",
            },
        )
        self.assertEqual(response.data["micro_interventions"], [])
        self.assertEqual(InteracaoAluno.objects.count(), 1)

    def test_social_message_obrigado_returns_empty_micro_interventions(self):
        response = self.client.post("/api/widget/chat/", {"message": "obrigado"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "social")
        self.assertEqual(response.data["emoji"], "🙌")
        self.assertEqual(response.data["micro_interventions"], [])

    @patch("brain.views.random.choice", return_value="Resposta B")
    def test_selects_random_reply_among_category_options(self, random_choice_mock):
        response = self.client.post("/api/widget/chat/", {"message": "zzmulti agora"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "multipla_teste")
        self.assertEqual(response.data["reply"], "Resposta B")
        random_choice_mock.assert_called()

    @patch("brain.views.random.choice", side_effect=["Resposta A", "Resposta B"])
    def test_avoids_immediate_reply_repetition_for_same_user(self, random_choice_mock):
        InteracaoAluno.objects.create(
            user=self.user,
            mensagem_usuario="mensagem anterior",
            categoria_detectada=self.multi_categoria,
            resposta_texto="Resposta A",
            origem="widget",
        )

        response = self.client.post("/api/widget/chat/", {"message": "zzmulti novamente"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reply"], "Resposta B")
        self.assertEqual(random_choice_mock.call_count, 2)

    @patch("brain.views.random.choice", return_value="Entendi. Me fala um pouco mais para eu poder te ajudar melhor.")
    def test_fallback_returns_null_category_and_no_micro_interventions(self, random_choice_mock):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "mensagem sem qualquer gatilho conhecido qwerty"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], None)
        self.assertEqual(response.data["emoji"], None)
        self.assertEqual(response.data["micro_interventions"], [])
        self.assertEqual(response.data["reply"], "Entendi. Me fala um pouco mais para eu poder te ajudar melhor.")
        random_choice_mock.assert_called()
