from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import HasInstitutionAccess, has_same_institution
from study_assistant.serializers import StudyAssistantAskSerializer, StudyAssistantResponseSerializer
from study_assistant.services import answer_study_question


class StudyAssistantAskView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasInstitutionAccess]

    @extend_schema(
        tags=["Study Assistant"],
        operation_id="study_assistant_ask",
        description="Recebe uma pergunta do aluno sobre como estudar melhor. Permissão: `student` com assinatura institucional válida e restrição ao escopo da própria instituição.",
        request=StudyAssistantAskSerializer,
        responses={
            200: OpenApiResponse(
                response=StudyAssistantResponseSerializer,
                examples=[
                    OpenApiExample(
                        "Study assistant answer",
                        value={
                            "intent": "study_guidance",
                            "subject": "quimica",
                            "language": "pt-BR",
                            "message": "Para aprender Química melhor, foque em uma rotina simples e consistente: ...",
                        },
                    )
                ],
            )
        },
    )
    def post(self, request):
        serializer = StudyAssistantAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.is_superuser and request.user.role != User.ROLE_STUDENT:
            return Response({"detail": "Apenas alunos podem usar o assistente de estudo."}, status=403)
        institution_id = serializer.validated_data.get("institution_id") or request.user.institution_id
        if not request.user.is_superuser and not has_same_institution(request.user, institution_id):
            return Response({"detail": "Instituicao fora do escopo do usuario."}, status=403)
        payload = answer_study_question(
            request.user,
            serializer.validated_data["message"],
            institution_id=institution_id,
        )
        return Response(StudyAssistantResponseSerializer(payload).data)
