# Teste de Notificacoes (MVP)

Checklist para validar email e WhatsApp em ambiente de teste:

1. Acessar `/login/` e clicar em **Primeiro acesso / Criar conta**.
2. Criar conta com telefone e permitir WhatsApp.
3. Fazer login.
4. Criar uma tarefa com data para hoje/amanha.
5. Criar um evento na agenda para +2 minutos.
6. Criar uma regra de lembrete (minutos antes) com canal **EMAIL** e **WHATSAPP**.
7. Em **Lembretes**, clicar em **Gerar lembretes**.
8. Verificar recebimento por email e WhatsApp.
9. Responder **2** e confirmar novo lembrete em 10 minutos.
10. Responder **1** e confirmar status no historico.
11. Responder **3** e confirmar cancelamento no historico.

Observacao: o webhook deve estar configurado no Meta WhatsApp Cloud com o endpoint:
`/api/notifications/whatsapp/webhook/`.
