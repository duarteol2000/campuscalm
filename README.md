# Campus Calm (MVP)

MVP para universitarios acompanharem o semestre com bem-estar, organizacao e foco. O projeto usa Django + Django REST Framework, autenticacao JWT e banco SQLite em dev.

## Requisitos
- Python 3.12+
- Pip

## Setup rapido
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Variaveis de ambiente
Copie `.env.example` e ajuste conforme necessario. A variavel `TRIAGE_USE_LLM` prepara a triagem para LLM futuro (mock no MVP).

## Endpoints principais
- Auth: `/api/auth/register/`, `/api/auth/login/`, `/api/auth/refresh/`, `/api/auth/me/`
- Billing: `/api/billing/plan/`, `/api/billing/set-plan/` (admin)
- Onboarding: `/api/onboarding/status/`
- Mood: `/api/mood/entries/`, `/api/mood/summary/weekly/`
- Pomodoro: `/api/pomodoro/start/`, `/api/pomodoro/stop/{id}/`, `/api/pomodoro/summary/weekly/`
- Planner: `/api/planner/tasks/`
- Agenda: `/api/agenda/events/`, `/api/agenda/week/`, `/api/agenda/generate-reminders/`
- Semester: `/api/semester/semesters/`, `/api/semester/courses/`, `/api/semester/assessments/`, `/api/semester/courses/{id}/progress/`, `/api/semester/finish/{semester_id}/`
- Content: `/api/content/guided/`, `/api/content/guided/{id}/`
- Notifications: `/api/notifications/test-email/`, `/api/notifications/pending/`
- Access Requests: `/api/access/requests/`, `/api/access/requests/{id}/approve/`, `/api/access/requests/{id}/reject/`, `/api/access/triage/{id}/log/`
- Analytics: `/api/analytics/dashboard/`, `/api/analytics/semester/{semester_id}/`

## Documentacao automatica
- Schema: `/api/schema/`
- Swagger UI: `/api/docs/`

## Exemplos com curl
### Registrar
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"aluno@exemplo.com","name":"Aluno","password":"senha123"}'
```

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"aluno@exemplo.com","password":"senha123"}'
```

### Criar check-in de humor
```bash
curl -X POST http://localhost:8000/api/mood/entries/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"mood":"OK","notes":"Dia produtivo"}'
```

### Criar tarefa
```bash
curl -X POST http://localhost:8000/api/planner/tasks/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Trabalho final","due_date":"2026-03-10","stress_level":3,"status":"TODO"}'
```

### Criar regra de lembrete e gerar notificacoes
```bash
curl -X POST http://localhost:8000/api/agenda/reminder-rules/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"target_type":"TASK","remind_before_minutes":60,"channels":["EMAIL"],"is_active":true}'

curl -X POST http://localhost:8000/api/agenda/generate-reminders/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Solicitar acesso (triagem automatica)
```bash
curl -X POST http://localhost:8000/api/access/requests/ \
  -H "Content-Type: application/json" \
  -d '{"requester_email":"coord@faculdade.com","requester_type":"INSTITUTION","estimated_users":120}'
```

## Health-check
```bash
curl http://localhost:8000/health/
```

## Script de demo (curl)
```bash
bash scripts/run_curl_demo.sh
```

## Seed de dados (mais completo)
```bash
python manage.py seed_demo_data --email nari.naluu@gmail.com
```

## Notificacoes
- Email: backend console em dev.
- WhatsApp/SMS: mock no MVP.

Processar fila manualmente:
```bash
python manage.py process_notification_queue
```

## Sistema de mensagens
O Campus Calm usa um **Message Framework** centralizado em `utils/messages.py`.
- Tipos: REMINDER, CARE, INCENTIVE, WARNING, ACHIEVEMENT, SYSTEM
- Canais: IN_APP (sempre), EMAIL (conforme plano), WHATSAPP/SMS (mock)
- Todas as mensagens usam tom calmo e nao clinico.

As mensagens ficam registradas em `notifications.NotificationQueue`.

## Progresso academico
Os calculos de progresso ficam em `utils/academic_progress.py`:
- **media ponderada** por peso
- **progress_percent** limitado a 100%
- **needed_to_pass** nunca negativo

Regras de status:
- progress_percent >= 100% -> PASSED
- semestre finalizado e progress_percent < 100% -> FAILED
- caso contrario -> IN_PROGRESS

Mensagens automaticas:
- Nova nota: INCENTIVE (progresso subiu) ou CARE (progresso caiu)
- Progresso < 70% com avaliacao proxima: WARNING suave
- Disciplina atinge 100%: ACHIEVEMENT
- Finalizar semestre: ACHIEVEMENT se todas aprovadas; CARE + INCENTIVE se alguma reprovada

## Observacoes de seguranca
- O sistema nao e um dispositivo medico.
- Em humor muito baixo recorrente, o sistema recomenda apoio profissional (ex: CVV 188).

## Tests
```bash
python manage.py test
```
