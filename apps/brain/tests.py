from unittest.mock import patch
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from agenda.models import CalendarEvent
from brain.constants import CONTEXT_MESSAGES
from brain.models import (
    CategoriaEmocional,
    ChatPendingAction,
    GatilhoEmocional,
    InteracaoAluno,
    MicroIntervencao,
    RespostaEmocional,
)
from brain.views import BLINDAGEM_NEUTRAL_REPLY, BLINDAGEM_REPLY
from notifications.models import InAppNotification
from planner.models import Task
from utils.constants import EVENT_PROVA

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

    def _create_interacao_custom(self, categoria_slug, resposta_texto, hours_ago):
        categoria = CategoriaEmocional.objects.get(slug=categoria_slug)
        interaction = InteracaoAluno.objects.create(
            user=self.user,
            mensagem_usuario=f"custom-{categoria_slug}-{hours_ago}",
            categoria_detectada=categoria,
            resposta_texto=resposta_texto,
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

    def test_greeting_message_returns_greeting_reply(self):
        response = self.client.post("/api/widget/chat/", {"message": "bom dia"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reply"], "Bom dia! Como posso te ajudar hoje?")
        self.assertEqual(response.data["category"], None)
        self.assertEqual(response.data["emoji"], None)
        self.assertEqual(response.data["micro_interventions"], [])

    def test_greeting_message_uppercase_returns_greeting_reply(self):
        response = self.client.post("/api/widget/chat/", {"message": "BOM DIA!!!"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reply"], "Bom dia! Como posso te ajudar hoje?")
        self.assertEqual(response.data["category"], None)
        self.assertEqual(response.data["emoji"], None)
        self.assertEqual(response.data["micro_interventions"], [])

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

    def test_detects_stress_anxiety_before_exam(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "vou fazer uma prova e estou muito ansioso"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_anxiety"])
        self.assertLessEqual(len(response.data["micro_interventions"]), 1)

    def test_detects_stress_anxiety_general_message(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "o que mais posso fazer pra melhorar minha ansiedade?"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_anxiety"])
        self.assertLessEqual(len(response.data["micro_interventions"]), 1)

    def test_detects_stress_anxiety_with_common_typo(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "boa tarde, vou fazer uma prova e estou muito ancioso"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_anxiety"])
        self.assertLessEqual(len(response.data["micro_interventions"]), 1)

    def test_weak_positive_with_negative_context_falls_back_to_stress(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "show, mas estou muito ansioso para a prova"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")

    def test_weak_positive_preserved_when_message_is_positive(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "show, consegui terminar tudo"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "evolucao")

    def test_strong_positive_phrase_remains_evolucao(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "que massa, consegui tirar boa nota"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "evolucao")

    def test_micro_interventions_are_limited_to_one_when_present(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "estou sobrecarregado com prazo e estressado"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertLessEqual(len(response.data["micro_interventions"]), 1)

    def test_micro_intervention_avoids_immediate_repeat_when_multiple_options(self):
        first = self.client.post(
            "/api/widget/chat/",
            {"message": "estou sobrecarregado e estressado"},
            format="json",
        )
        second = self.client.post(
            "/api/widget/chat/",
            {"message": "ainda estou sobrecarregado e estressado"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertLessEqual(len(first.data["micro_interventions"]), 1)
        self.assertLessEqual(len(second.data["micro_interventions"]), 1)

        if first.data["micro_interventions"] and second.data["micro_interventions"]:
            first_name = first.data["micro_interventions"][0]["nome"]
            second_name = second.data["micro_interventions"][0]["nome"]
            if MicroIntervencao.objects.filter(ativo=True).count() > 1:
                self.assertNotEqual(first_name, second_name)

    def test_short_direction_intent_returns_stress_guidance_main(self):
        self.client.post(
            "/api/widget/chat/",
            {"message": "Estou com medo de nao conseguir passar na prova"},
            format="json",
        )

        response = self.client.post(
            "/api/widget/chat/",
            {"message": "O que faco?"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_short_direction_main"])
        self.assertNotEqual(response.data["reply"], "Estou aqui com voce. Quer me contar um pouco mais sobre isso?")
        self.assertEqual(response.data["micro_interventions"], [])

    def test_short_direction_new_variations_trigger_main_with_stress_context(self):
        variations = [
            "q faco",
            "oq eu faco?",
            "o que eu faço?",
            "oq fazer",
            "que faço",
            "me ajuda pf",
            "me ajuda por favor",
        ]

        for message in variations:
            with self.subTest(message=message):
                InteracaoAluno.objects.filter(user=self.user).delete()
                self.client.post(
                    "/api/widget/chat/",
                    {"message": "Estou com medo e muito nervosa para a prova"},
                    format="json",
                )
                response = self.client.post("/api/widget/chat/", {"message": message}, format="json")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["category"], "stress")
                self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_short_direction_main"])
                self.assertEqual(response.data["micro_interventions"], [])

    def test_short_direction_new_variation_without_stress_context_uses_normal_flow(self):
        response = self.client.post("/api/widget/chat/", {"message": "q faco"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(response.data["reply"], CONTEXT_MESSAGES["stress_short_direction_main"])

    def test_short_direction_english_triggers_main_with_stress_context(self):
        self.client.post(
            "/api/widget/chat/",
            {"message": "I'm nervous about my exam"},
            format="json",
        )

        response = self.client.post(
            "/api/widget/chat/",
            {"message": "What should I do?"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_short_direction_main_en"])
        self.assertEqual(response.data["micro_interventions"], [])

    def test_short_direction_english_followup_positive_closes_flow(self):
        self.client.post(
            "/api/widget/chat/",
            {"message": "I'm nervous about my exam"},
            format="json",
        )
        self.client.post(
            "/api/widget/chat/",
            {"message": "What should I do?"},
            format="json",
        )

        response = self.client.post(
            "/api/widget/chat/",
            {"message": "better"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_short_direction_ok_en"])
        self.assertEqual(response.data["micro_interventions"], [])

    def test_short_direction_english_followup_negative_returns_body_regulation(self):
        self.client.post(
            "/api/widget/chat/",
            {"message": "I'm nervous about my exam"},
            format="json",
        )
        self.client.post(
            "/api/widget/chat/",
            {"message": "What should I do?"},
            format="json",
        )

        response = self.client.post(
            "/api/widget/chat/",
            {"message": "still nervous"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_short_direction_body_en"])
        self.assertEqual(response.data["micro_interventions"], [])

    def test_short_direction_english_without_stress_context_uses_normal_flow(self):
        response = self.client.post("/api/widget/chat/", {"message": "What should I do?"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(response.data["reply"], CONTEXT_MESSAGES["stress_short_direction_main_en"])

    def test_language_cookie_en_returns_english_fallback_for_unknown_message(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "blabla unknown text without specific trigger"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], None)
        self.assertIn(response.data["reply"], {"I'm here with you. Can you tell me a little more about this?", "Got it. Tell me a bit more so I can help you better."})

    def test_language_cookie_en_detects_stress_and_replies_in_english(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "I am very anxious about my exam tomorrow"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_anxiety_en"])
        self.assertLessEqual(len(response.data["micro_interventions"]), 1)
        if response.data["micro_interventions"]:
            micro = response.data["micro_interventions"][0]
            self.assertIn(
                micro["nome"],
                {"Drink water", "Breathing 4-4-4"},
            )

    def test_language_cookie_en_detects_social_and_replies_in_english(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "thank you, I appreciate it"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "social")
        self.assertIn(response.data["reply"], {"Happy to help.", "Anytime you need, I'm here.", "You can count on me."})
        self.assertEqual(response.data["micro_interventions"], [])

    def test_short_direction_followup_positive_closes_flow(self):
        self.client.post(
            "/api/widget/chat/",
            {"message": "Estou com medo de nao conseguir passar na prova"},
            format="json",
        )
        self.client.post(
            "/api/widget/chat/",
            {"message": "O que faco?"},
            format="json",
        )

        response = self.client.post(
            "/api/widget/chat/",
            {"message": "melhorou"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_short_direction_ok"])
        self.assertEqual(response.data["micro_interventions"], [])

    def test_short_direction_followup_negative_returns_body_regulation(self):
        self.client.post(
            "/api/widget/chat/",
            {"message": "Estou com medo de nao conseguir passar na prova"},
            format="json",
        )
        self.client.post(
            "/api/widget/chat/",
            {"message": "O que faco?"},
            format="json",
        )

        response = self.client.post(
            "/api/widget/chat/",
            {"message": "nao resolveu, ainda to nervosa"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_short_direction_body"])
        self.assertEqual(response.data["micro_interventions"], [])

    def test_short_direction_second_o_que_faco_returns_body_regulation(self):
        self.client.post(
            "/api/widget/chat/",
            {"message": "Estou com medo de nao conseguir passar na prova"},
            format="json",
        )
        self.client.post(
            "/api/widget/chat/",
            {"message": "O que faco?"},
            format="json",
        )

        response = self.client.post(
            "/api/widget/chat/",
            {"message": "o que faco"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_short_direction_body"])
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
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_repeat"])

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
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["evolucao_repeat"])
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
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_to_evolucao"])
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
        self.assertNotIn(response.data["reply"], CONTEXT_MESSAGES["stress_repeat"])

    def test_contextual_memory_avoids_immediate_repeat_variant(self):
        repeated_text = CONTEXT_MESSAGES["stress_repeat"][0]
        self._create_interacao_custom("stress", repeated_text, 1)
        self._create_interacao_with_hours_ago("stress", 2)
        self._create_interacao_with_hours_ago("stress", 3)

        response = self.client.post(
            "/api/widget/chat/",
            {"message": "Estou muito sobrecarregado e estressado"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertIn(response.data["reply"], CONTEXT_MESSAGES["stress_repeat"])
        self.assertNotEqual(response.data["reply"], repeated_text)

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

    @patch("brain.views.choose_variant", return_value="Resposta B")
    def test_selects_random_reply_among_category_options(self, choose_variant_mock):
        response = self.client.post("/api/widget/chat/", {"message": "zzmulti agora"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "multipla_teste")
        self.assertEqual(response.data["reply"], "Resposta B")
        choose_variant_mock.assert_called()

    @patch("brain.views.choose_variant", return_value="Resposta B")
    def test_avoids_immediate_reply_repetition_for_same_user(self, choose_variant_mock):
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
        self.assertNotEqual(response.data["reply"], "Resposta A")
        choose_variant_mock.assert_called()

    def test_blindagem_activates_after_two_null_classifications(self):
        first = self.client.post(
            "/api/widget/chat/",
            {"message": "texto sem gatilho alfa"},
            format="json",
        )
        second = self.client.post(
            "/api/widget/chat/",
            {"message": "texto sem gatilho beta"},
            format="json",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["category"], None)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["category"], None)
        self.assertEqual(second.data["reply"], BLINDAGEM_REPLY)
        self.assertEqual(second.data["micro_interventions"], [])

    def test_blindagem_choice_ansiedade_maps_directly_to_stress(self):
        self.client.post("/api/widget/chat/", {"message": "texto sem gatilho alfa"}, format="json")
        self.client.post("/api/widget/chat/", {"message": "texto sem gatilho beta"}, format="json")

        response = self.client.post("/api/widget/chat/", {"message": "ansiedade"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertNotEqual(response.data["reply"], BLINDAGEM_REPLY)
        self.assertTrue(response.data["reply"])

    def test_blindagem_does_not_activate_when_second_message_is_classified(self):
        self.client.post("/api/widget/chat/", {"message": "texto sem gatilho alfa"}, format="json")
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "estou muito ansioso para a prova"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertNotEqual(response.data["reply"], BLINDAGEM_REPLY)

    def test_blindagem_anti_loop_returns_neutral_guidance(self):
        self.client.post("/api/widget/chat/", {"message": "texto sem gatilho alfa"}, format="json")
        self.client.post("/api/widget/chat/", {"message": "texto sem gatilho beta"}, format="json")
        response = self.client.post("/api/widget/chat/", {"message": "texto sem gatilho gama"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], None)
        self.assertEqual(response.data["reply"], BLINDAGEM_NEUTRAL_REPLY)
        self.assertEqual(response.data["micro_interventions"], [])

    def test_task_concierge_two_step_flow_creates_task_and_notification(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        first = self.client.post(
            "/api/widget/chat/",
            {"message": "Crie uma tarefa"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertIn("Qual a descricao da tarefa", first.data["reply"])

        second = self.client.post(
            "/api/widget/chat/",
            {"message": "Revisar Arquitetura de Máquinas"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertIn("Qual a data e hora de entrega", second.data["reply"])

        third = self.client.post(
            "/api/widget/chat/",
            {"message": "amanhã 18h"},
            format="json",
        )
        self.assertEqual(third.status_code, 200)
        self.assertIn("✅ Tarefa criada:", third.data["reply"])
        self.assertIn("🔔 Veja em Tarefas", third.data["reply"])

        task = Task.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(task)
        self.assertEqual(task.due_date, tomorrow)
        self.assertIn("revisar arquitetura", task.title)

        notification = InAppNotification.objects.filter(user=self.user, title="Tarefa criada").order_by("-id").first()
        self.assertIsNotNone(notification)
        self.assertIn(f"highlight_task={task.id}", notification.target_url)
        self.assertFalse(ChatPendingAction.objects.filter(user=self.user).exists())

    def test_task_concierge_skips_step_one_when_title_is_clear(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        first = self.client.post(
            "/api/widget/chat/",
            {"message": 'Crie tarefa: "Arquitetura de Máquinas"'},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertIn("Qual a data e hora de entrega", first.data["reply"])

        second = self.client.post(
            "/api/widget/chat/",
            {"message": "25/02 09:00"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertIn("✅ Tarefa criada:", second.data["reply"])

        task = Task.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(task)
        self.assertEqual(task.due_date, date(tomorrow.year, 2, 25))
        self.assertIn("arquitetura de máquinas", task.title.lower())

    def test_task_concierge_generic_quero_criar_asks_scope_first(self):
        first = self.client.post(
            "/api/widget/chat/",
            {"message": "quero criar uma tarefa"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertIn("Qual a descricao da tarefa", first.data["reply"])

        pending = ChatPendingAction.objects.filter(user=self.user).first()
        self.assertIsNotNone(pending)
        self.assertEqual(pending.step, 1)
        self.assertEqual(pending.draft_title, "")

        second = self.client.post(
            "/api/widget/chat/",
            {"message": "Entregar trabalho do professor fulano"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertIn("Qual a data e hora de entrega", second.data["reply"])

    def test_event_concierge_two_step_flow_creates_event_and_notification(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        first = self.client.post(
            "/api/widget/chat/",
            {"message": "Agende uma reuniao"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertIn("Qual o compromisso na agenda", first.data["reply"])

        second = self.client.post(
            "/api/widget/chat/",
            {"message": "Reuniao com professor"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertIn("data e hora", second.data["reply"])

        third = self.client.post(
            "/api/widget/chat/",
            {"message": "amanha 14h"},
            format="json",
        )
        self.assertEqual(third.status_code, 200)
        self.assertIn("Evento criado", third.data["reply"])
        self.assertIn("Veja em Agenda", third.data["reply"])

        event = CalendarEvent.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(timezone.localtime(event.start_at).date(), tomorrow)
        self.assertEqual(timezone.localtime(event.start_at).time().hour, 14)

        notification = InAppNotification.objects.filter(user=self.user, title="Evento agendado").order_by("-id").first()
        self.assertIsNotNone(notification)
        self.assertIn(f"highlight_event={event.id}", notification.target_url)
        self.assertFalse(ChatPendingAction.objects.filter(user=self.user).exists())

    def test_event_concierge_generic_request_asks_scope_first(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "quero criar uma agenda"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Qual o compromisso na agenda", response.data["reply"])

        pending = ChatPendingAction.objects.filter(user=self.user).first()
        self.assertIsNotNone(pending)
        self.assertEqual(pending.pending_action, "create_event")
        self.assertEqual(pending.step, 1)
        self.assertEqual((pending.draft_title or "").strip(), "")

    def test_event_concierge_step_two_shows_type_options(self):
        self.client.post("/api/widget/chat/", {"message": "quero criar uma agenda"}, format="json")
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "Reuniao com professor"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Qual o tipo do evento?", response.data["reply"])
        self.assertIn("prova, entrega, aula, reuniao, outro", response.data["reply"])
        self.assertIn("data e hora", response.data["reply"])

    def test_event_concierge_accepts_explicit_type_choice(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.client.post("/api/widget/chat/", {"message": "quero criar uma agenda"}, format="json")
        self.client.post(
            "/api/widget/chat/",
            {"message": "Revisao final"},
            format="json",
        )
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "prova amanha 14h"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Evento criado", response.data["reply"])

        event = CalendarEvent.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, EVENT_PROVA)
        self.assertEqual(timezone.localtime(event.start_at).date(), tomorrow)

    def test_event_concierge_accepts_type_only_then_asks_only_datetime(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.client.post("/api/widget/chat/", {"message": "quero criar uma agenda"}, format="json")
        self.client.post(
            "/api/widget/chat/",
            {"message": "Prova de cálculo"},
            format="json",
        )

        third = self.client.post(
            "/api/widget/chat/",
            {"message": "prova"},
            format="json",
        )
        self.assertEqual(third.status_code, 200)
        self.assertIn("data e hora", third.data["reply"])
        self.assertEqual(CalendarEvent.objects.filter(user=self.user).count(), 0)

        pending = ChatPendingAction.objects.filter(user=self.user).first()
        self.assertIsNotNone(pending)
        self.assertEqual(pending.pending_action, "create_event")
        self.assertEqual(pending.step, 2)

        fourth = self.client.post(
            "/api/widget/chat/",
            {"message": "amanha 14h"},
            format="json",
        )
        self.assertEqual(fourth.status_code, 200)
        self.assertIn("✅ Evento criado:", fourth.data["reply"])
        self.assertIn("🔔 Veja em Agenda", fourth.data["reply"])

        event = CalendarEvent.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, EVENT_PROVA)
        self.assertEqual(timezone.localtime(event.start_at).date(), tomorrow)

    def test_event_concierge_does_not_advance_on_emotional_message(self):
        first = self.client.post(
            "/api/widget/chat/",
            {"message": "Agende uma reuniao"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertIn("Qual o compromisso na agenda", first.data["reply"])

        pending_before = ChatPendingAction.objects.filter(user=self.user).first()
        self.assertIsNotNone(pending_before)
        self.assertEqual(pending_before.pending_action, "create_event")
        self.assertEqual(pending_before.step, 1)

        second = self.client.post(
            "/api/widget/chat/",
            {"message": "to muito ansioso hoje"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["category"], "stress")

        pending_after = ChatPendingAction.objects.filter(user=self.user).first()
        self.assertIsNotNone(pending_after)
        self.assertEqual(pending_after.pending_action, "create_event")
        self.assertEqual(pending_after.step, 1)
        self.assertEqual(CalendarEvent.objects.filter(user=self.user).count(), 0)

    def test_intent_scoring_conflict_emotional_and_event_prioritizes_emotional_support(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "Estou ansioso porque tenho prova amanhã às 9h"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "stress")
        self.assertEqual(Task.objects.filter(user=self.user).count(), 0)
        self.assertEqual(CalendarEvent.objects.filter(user=self.user).count(), 0)
        self.assertFalse(ChatPendingAction.objects.filter(user=self.user).exists())

    def test_intent_scoring_conflict_task_and_event_prioritizes_event(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "Revisar cálculo amanhã às 14h"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("data e hora", response.data["reply"])
        pending = ChatPendingAction.objects.filter(user=self.user).first()
        self.assertIsNotNone(pending)
        self.assertEqual(pending.pending_action, "create_event")
        self.assertEqual(Task.objects.filter(user=self.user).count(), 0)

    def test_intent_scoring_social_and_task_tie_prioritizes_task(self):
        response = self.client.post(
            "/api/widget/chat/",
            {"message": "Bom dia, preciso estudar"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        pending = ChatPendingAction.objects.filter(user=self.user).first()
        self.assertIsNotNone(pending)
        self.assertEqual(pending.pending_action, "create_task")
        self.assertIn("Criando nova tarefa", response.data["reply"])

    def test_intent_scoring_with_pending_event_keeps_event_flow(self):
        first = self.client.post(
            "/api/widget/chat/",
            {"message": "Agende uma reuniao"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/widget/chat/",
            {"message": "Reuniao com professor"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertIn("data e hora", second.data["reply"])

        pending = ChatPendingAction.objects.filter(user=self.user).first()
        self.assertIsNotNone(pending)
        self.assertEqual(pending.pending_action, "create_event")
        self.assertEqual(pending.step, 2)

    def test_task_concierge_cancel_stops_flow_without_creating_task(self):
        self.client.post("/api/widget/chat/", {"message": "Crie uma tarefa"}, format="json")
        response = self.client.post("/api/widget/chat/", {"message": "cancelar"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("cancelei", response.data["reply"].lower())
        self.assertEqual(Task.objects.filter(user=self.user).count(), 0)
        self.assertFalse(ChatPendingAction.objects.filter(user=self.user).exists())

    def test_task_concierge_parses_time_without_confusing_day_from_date(self):
        first = self.client.post(
            "/api/widget/chat/",
            {"message": "Crie uma tarefa: Sistemas e Modelos"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertIn("Qual a data e hora de entrega", first.data["reply"])

        second = self.client.post(
            "/api/widget/chat/",
            {"message": "23/02/2026 as 10 horas"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertIn("✅ Tarefa criada:", second.data["reply"])

        task = Task.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(task)
        self.assertEqual(task.due_date, date(2026, 2, 23))
        self.assertIn("Horario sugerido: 10:00", task.description)
        self.assertNotIn("Crie uma tarefa", task.description)

    def test_task_concierge_uses_only_scope_in_description(self):
        first = self.client.post(
            "/api/widget/chat/",
            {"message": "Bom dia gostaria de criar uma tarefa para a disciplina de computacao: Arquitetura de hardware"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertIn("Qual a data e hora de entrega", first.data["reply"])

        second = self.client.post(
            "/api/widget/chat/",
            {"message": "23/02/2026 as 11 horas"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertIn("✅ Tarefa criada:", second.data["reply"])

        task = Task.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(task)
        self.assertIn("Arquitetura de hardware", task.description)
        self.assertIn("Horario sugerido: 11:00", task.description)
        self.assertNotIn("Bom dia gostaria de criar uma tarefa", task.description)

    def test_task_concierge_parses_textual_time_words(self):
        first = self.client.post(
            "/api/widget/chat/",
            {"message": "Crie uma tarefa: Revisar Sistemas"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertIn("Qual a data e hora de entrega", first.data["reply"])

        second = self.client.post(
            "/api/widget/chat/",
            {"message": "23/02/2026 as dez e meia"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertIn("✅ Tarefa criada:", second.data["reply"])

        task = Task.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(task)
        self.assertEqual(task.due_date, date(2026, 2, 23))
        self.assertIn("Horario sugerido: 10:30", task.description)

    def test_task_concierge_does_not_advance_on_emotional_message(self):
        first = self.client.post(
            "/api/widget/chat/",
            {"message": "Crie uma tarefa"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertIn("Qual a descricao da tarefa", first.data["reply"])

        pending_before = ChatPendingAction.objects.filter(user=self.user).first()
        self.assertIsNotNone(pending_before)
        self.assertEqual(pending_before.step, 1)
        self.assertEqual(pending_before.draft_description, "")

        second = self.client.post(
            "/api/widget/chat/",
            {"message": "Tô muito ansioso hoje"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["category"], "stress")

        pending_after = ChatPendingAction.objects.filter(user=self.user).first()
        self.assertIsNotNone(pending_after)
        self.assertEqual(pending_after.step, 1)
        self.assertEqual(pending_after.draft_description, "")
        self.assertEqual(Task.objects.filter(user=self.user).count(), 0)

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
