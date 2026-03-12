# Technical Changelog

## 2026-03-12

### OpenAPI global cleanup

- normalizado o schema global do `drf-spectacular` por módulos, preservando compatibilidade da API existente
- adicionados `serializer_class` e `@extend_schema(...)` nas `APIView`s que estavam sem contrato explícito
- adicionados `operation_id` explícitos para remover colisões no schema
- tipados parâmetros de rota dos `ViewSet`s afetados com `OpenApiParameter(..., PATH)`
- adicionados type hints e `@extend_schema_field(...)` em campos calculados do módulo `semester`
- adicionados serializers auxiliares de request/response para contratos antes implícitos
- configurado `ENUM_NAME_OVERRIDES` em [settings.py](/home/marcosdo/projetos/campuscalm/config/settings.py) para resolver enums ambíguos no schema
- ajustado também o módulo `onboarding`, que continuava aparecendo no OpenAPI global
- regenerado o arquivo exportado [openapi-campuscalm.yaml](/home/marcosdo/projetos/campuscalm/docs/openapi-campuscalm.yaml) sem warnings e sem errors

### CI recommendation applied

- adicionado workflow GitHub Actions para validar o schema OpenAPI em toda alteração
- a verificação usa:
  - instalação via `requirements.txt`
  - banco SQLite temporário
  - comando `manage.py spectacular --file docs/openapi-campuscalm.yaml --fail-on-warn`
- objetivo: falhar o pipeline sempre que o schema voltar a gerar warning ou error
