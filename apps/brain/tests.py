from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from brain.constants import CONTEXT_MESSAGES
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

    def _create_interacao_with_hours_ago(self, categoria_slug, hours_ago):
        categoria = CategoriaEmocional.objects.get(slug=categoria_slug)
        interaction = InteracaoAluno.objects.create(
            user=self.user,
            mensagem_usuario=f"hist-{categoria_slug}-{hours_ago}",
            categoria_detectada=categoria,
            resposta_texto=f"resp-{categoria_slug}",
            origem="widget",
        )
        timestamp = timezone.now() - timedelta(hours=hours_ago)
        InteracaoAluno.objects.filter(pk=interaction.pk).update(created_at=timestamp)
        interaction.refresh_from_db()
        return interaction

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

    def test_detects_evolucao_category(self):
        response = self.client.post("/api/widget/chat/", {"message": "Consegui, to indo bem e evolui"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "evolucao")
        self.assertEqual(response.data["emoji"], "📈")
        self.assertTrue(response.data["reply"])
        self.assertEqual(response.data["micro_interventions"], [])

    def test_detects_evolucao_with_student_slang(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "Que massa, show, top, consegui!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "evolucao")
        self.assertEqual(response.data["emoji"], "📈")
        self.assertTrue(response.data["reply"])
        self.assertEqual(response.data["micro_interventions"], [])

    def test_detects_evolucao_with_maravilha_slang(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "Maravilha, hoje mandei bem!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "evolucao")
        self.assertEqual(response.data["emoji"], "📈")
        self.assertTrue(response.data["reply"])
        self.assertEqual(response.data["micro_interventions"], [])

    def test_contextual_memory_stress_repetition_within_48h(self):
        self._create_interacao_with_hours_ago("stress", 2)
        self._create_interacao_with_hours_ago("stress", 4)
        self._create_interacao_with_hours_ago("stress", 6)

        response = self.client.post(
            "/api/widget/chat/",
            {"message": "Estou muito sobrecarregado e estressado"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertEqual(response.data["reply"], CONTEXT_MESSAGES["stress_repeat"])

    def test_contextual_memory_repeated_evolucao_within_48h(self):
        self._create_interacao_with_hours_ago("evolucao", 3)
        self._create_interacao_with_hours_ago("evolucao", 5)

        response = self.client.post(
            "/api/widget/chat/",
            {"message": "Consegui, to indo bem"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "evolucao")
        self.assertEqual(response.data["reply"], CONTEXT_MESSAGES["evolucao_repeat"])
        self.assertEqual(response.data["micro_interventions"], [])

    def test_contextual_memory_stress_to_evolucao_within_24h(self):
        self._create_interacao_with_hours_ago("stress", 12)

        response = self.client.post(
            "/api/widget/chat/",
            {"message": "Consegui bater a meta, to indo bem"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "evolucao")
        self.assertEqual(response.data["reply"], CONTEXT_MESSAGES["stress_to_evolucao"])
        self.assertEqual(response.data["micro_interventions"], [])

    def test_contextual_memory_ignores_interactions_older_than_48h(self):
        self._create_interacao_with_hours_ago("stress", 50)
        self._create_interacao_with_hours_ago("stress", 60)
        self._create_interacao_with_hours_ago("stress", 70)

        response = self.client.post(
            "/api/widget/chat/",
            {"message": "Estou muito sobrecarregado e estressado"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertNotEqual(response.data["reply"], CONTEXT_MESSAGES["stress_repeat"])

    def test_long_positive_message_prefers_evolucao_over_stress(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "eu estudei bastante, com bastante foco e consegui tirar uma boa nota na prova"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "evolucao")
        self.assertEqual(response.data["emoji"], "📈")
        self.assertEqual(response.data["micro_interventions"], [])

    def test_primary_categories_have_at_least_four_active_replies(self):
        category_slugs = ["stress", "duvida", "motivacao_baixa", "cansaco_mental", "foco_alto"]
        for slug in category_slugs:
            categoria = CategoriaEmocional.objects.filter(slug=slug).first()
            self.assertIsNotNone(categoria)
            active_count = RespostaEmocional.objects.filter(categoria=categoria, ativo=True).count()
            self.assertGreaterEqual(active_count, 4)

    def test_evolucao_category_has_at_least_four_active_replies(self):
        categoria = CategoriaEmocional.objects.filter(slug="evolucao").first()
        self.assertIsNotNone(categoria)
        active_count = RespostaEmocional.objects.filter(categoria=categoria, ativo=True).count()
        self.assertGreaterEqual(active_count, 4)

    def test_endpoint_typical_messages_for_primary_categories(self):
        samples = [
            ("stress", "Estou sobrecarregado com prazo"),
            ("duvida", "Nao entendi essa materia"),
            ("motivacao_baixa", "Estou desmotivado hoje"),
            ("cansaco_mental", "Estou esgotado e sem energia"),
            ("foco_alto", "Hoje estou concentrado e produtivo"),
        ]
        for expected_slug, message in samples:
            response = self.client.post("/api/widget/chat/", {"message": message}, format="json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["category"], expected_slug)
            self.assertTrue(response.data["reply"])

    def test_scoring_phrase_weight_wins_over_single_word(self):
        phrase_categoria = CategoriaEmocional.objects.create(nome="Score Frase", slug="score_frase_teste", emoji="🔍")
        word_categoria = CategoriaEmocional.objects.create(nome="Score Palavra", slug="score_palavra_teste", emoji="🧪")

        GatilhoEmocional.objects.create(categoria=phrase_categoria, palavras_chave="mega progresso")
        GatilhoEmocional.objects.create(categoria=word_categoria, palavras_chave="mega")

        RespostaEmocional.objects.create(categoria=phrase_categoria, texto="Resposta categoria frase")
        RespostaEmocional.objects.create(categoria=word_categoria, texto="Resposta categoria palavra")

        response = self.client.post("/api/widget/chat/", {"message": "hoje foi mega progresso"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "score_frase_teste")
        self.assertEqual(response.data["emoji"], "🔍")
        self.assertTrue(response.data["reply"])

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
