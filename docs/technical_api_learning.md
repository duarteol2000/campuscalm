# CampusCalm Learning APIs

Documentação técnica curta para os endpoints de dashboards e do `study_assistant`.

## OpenAPI

- Schema JSON: `GET /api/schema/`
- Swagger UI: `GET /api/docs/`

## 1. Student dashboard

- Rota: `GET /api/learning/dashboard/student/`
- Permissão: usuário autenticado com `role=student` e assinatura institucional válida
- Exemplo de request:

```http
GET /api/learning/dashboard/student/ HTTP/1.1
Cookie: sessionid=<session>
Accept: application/json
```

- Exemplo de response:

```json
{
  "score_current": {
    "score_value": 720,
    "classification": "disciplinado",
    "calculated_at": "2026-03-12T10:00:00Z"
  },
  "score_evolution": [
    {
      "score_value": 680,
      "classification": "organizado",
      "calculated_at": "2026-03-05T10:00:00Z"
    }
  ],
  "tasks_pending": [
    {
      "id": 1,
      "title": "Lista 1",
      "due_date": "2026-03-15"
    }
  ],
  "tasks_completed": [],
  "study_consistency": {
    "sessions_last_7_days": 4,
    "study_days_last_30_days": 12,
    "current_streak_days": 3
  },
  "achievements": [],
  "friendly_alerts": [
    "Sua consistência de estudo está baixa nesta semana."
  ],
  "recommendations": [
    "Comece com sessões de 25 minutos e pausas curtas de 5 minutos para reconstruir o hábito."
  ]
}
```

## 2. Parent dashboard

- Rota: `GET /api/learning/dashboard/parent/`
- Permissão: usuário autenticado com `role=parent` e assinatura institucional válida
- Exemplo de request:

```http
GET /api/learning/dashboard/parent/ HTTP/1.1
Cookie: sessionid=<session>
Accept: application/json
```

- Exemplo de response:

```json
{
  "children": [
    {
      "student_id": 3,
      "student_name": "Aluno Exemplo",
      "relationship_type": "responsavel",
      "score_current": {
        "score_value": 720,
        "classification": "disciplinado",
        "calculated_at": "2026-03-12T10:00:00Z"
      },
      "study_consistency": {
        "sessions_last_7_days": 4,
        "study_days_last_30_days": 12,
        "current_streak_days": 3
      },
      "tasks_completed": [],
      "friendly_alerts": []
    }
  ]
}
```

## 3. Teacher dashboard

- Rota: `GET /api/learning/dashboard/teacher/`
- Método: `GET`
- Permissão: usuário autenticado com `role=teacher`, `coordinator` ou `institution_admin`, assinatura válida e escopo restrito à própria instituição
- Query params: `class_group` opcional, `search` opcional, `page` opcional, `page_size` opcional, `institution_id` opcional apenas dentro do próprio escopo
- Exemplo de request:

```http
GET /api/learning/dashboard/teacher/?class_group=A HTTP/1.1
Cookie: sessionid=<session>
Accept: application/json
```

- Exemplo de response:

```json
{
  "class_average": 652.5,
  "students_at_risk": [],
  "students_low_consistency": [],
  "students_good_discipline": [
    {
      "student_id": 10,
      "student_name": "Ana",
      "class_group": "A",
      "score_value": 780,
      "classification": "disciplinado",
      "weekly_sessions": 5,
      "overdue_tasks": 0,
      "high_stress_events": 0
    }
  ],
  "pedagogical_insights": [
    "Há alunos com baixa consistência de estudo nesta turma."
  ],
  "ranking": [
    {
      "student_id": 10,
      "student_name": "Ana",
      "class_group": "A",
      "score_value": 780,
      "classification": "disciplinado",
      "weekly_sessions": 5,
      "overdue_tasks": 0,
      "high_stress_events": 0
    }
  ],
  "ranking_pagination": {
    "page": 1,
    "page_size": 10,
    "total_items": 1,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  },
  "ranking_filters": {
    "class_group": "A",
    "search": ""
  },
  "distribution": [
    {
      "classification": "disciplinado",
      "total": 3
    }
  ]
}
```

## 4. Institution dashboard

- Rota: `GET /api/learning/dashboard/institution/`
- Método: `GET`
- Permissão: usuário autenticado com `role=coordinator` ou `institution_admin`, assinatura válida e escopo restrito à própria instituição
- Exemplo de request:

```http
GET /api/learning/dashboard/institution/ HTTP/1.1
Cookie: sessionid=<session>
Accept: application/json
```

- Exemplo de response:

```json
{
  "institution_average": 688.33,
  "average_by_class": [
    {
      "class_group": "A",
      "average_score": 702.0,
      "students_total": 12
    }
  ],
  "students_at_risk": [],
  "class_ranking": [
    {
      "class_group": "A",
      "average_score": 702.0,
      "students_total": 12
    }
  ],
  "discipline_distribution": [
    {
      "classification": "disciplinado",
      "total": 8
    }
  ],
  "top_students": [
    {
      "student_id": 10,
      "student_name": "Ana",
      "class_group": "A",
      "score_value": 780,
      "classification": "disciplinado"
    }
  ],
  "pedagogical_insights": [
    "Alguns alunos apresentam risco de procrastinação."
  ]
}
```

## 5. Study assistant

- Rota: `POST /api/study-assistant/ask/`
- Permissão: usuário autenticado com `role=student` e assinatura institucional válida
- Exemplo de request:

```http
POST /api/study-assistant/ask/ HTTP/1.1
Cookie: sessionid=<session>
Content-Type: application/json
Accept: application/json

{
  "message": "nao to entendendo quimica"
}
```

- Exemplo de response:

```json
{
  "intent": "study_guidance",
  "subject": "quimica",
  "language": "pt-BR",
  "message": "Para aprender Química melhor, foque em uma rotina simples e consistente: ..."
}
```

## Arquivo exportado para entrega externa

- Export YAML: `docs/openapi-campuscalm.yaml`
