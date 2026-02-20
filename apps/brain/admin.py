from django.contrib import admin

from brain.models import (
    CategoriaEmocional,
    ChatPendingAction,
    GatilhoEmocional,
    InteracaoAluno,
    MicroIntervencao,
    RespostaEmocional,
)


@admin.register(CategoriaEmocional)
class CategoriaEmocionalAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "emoji", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "slug")


@admin.register(GatilhoEmocional)
class GatilhoEmocionalAdmin(admin.ModelAdmin):
    list_display = ("categoria", "ativo")
    list_filter = ("ativo", "categoria")
    search_fields = ("palavras_chave", "categoria__nome", "categoria__slug")


@admin.register(RespostaEmocional)
class RespostaEmocionalAdmin(admin.ModelAdmin):
    list_display = ("categoria", "ativo")
    list_filter = ("ativo", "categoria")
    search_fields = ("texto", "categoria__nome", "categoria__slug")


@admin.register(MicroIntervencao)
class MicroIntervencaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "texto")


@admin.register(InteracaoAluno)
class InteracaoAlunoAdmin(admin.ModelAdmin):
    list_display = ("user", "categoria_detectada", "origem", "created_at")
    list_filter = ("origem", "categoria_detectada", "created_at")
    search_fields = ("user__email", "mensagem_usuario", "resposta_texto")


@admin.register(ChatPendingAction)
class ChatPendingActionAdmin(admin.ModelAdmin):
    list_display = ("user", "pending_action", "step", "updated_at")
    list_filter = ("pending_action", "step", "updated_at")
    search_fields = ("user__email", "draft_title", "draft_description")
