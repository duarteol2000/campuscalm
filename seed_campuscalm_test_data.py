from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from random import Random

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import ParentProfile, StudentProfile, UserProfile
from billing.models import Institution, InstitutionSubscription, Plan, UserSubscription
from learning.models import Achievement, AcademicDisciplineScore, EmotionalCheckin, StudySession, StudyTask
from learning.services.discipline_score import classify_score
from utils.constants import PLAN_PRO


RNG = Random(20260313)
NOW = timezone.now()
TODAY = timezone.localdate()
PASSWORD = "CampusCalm123!"
INSTITUTION_CODE = "CCA_TEST"
INSTITUTION_SLUG = slugify("CampusCalm Academy")
CLASS_GROUPS = ("1A", "1B", "2A")
SUBJECTS = ("Matematica", "Portugues", "Fisica", "Quimica", "Biologia")
TASK_TEMPLATES = (
    "Lista de exercicios de matematica",
    "Leitura de capitulo de fisica",
    "Resumo de biologia",
    "Exercicios de interpretacao de texto",
    "Problemas de quimica",
)


@dataclass(frozen=True)
class StudentSeed:
    name: str
    email: str
    band: str
    class_group: str
    enrollment_number: str
    target_score: int


STUDENTS = [
    StudentSeed("Ana Luisa Duarte", "ana.luisa@campuscalm.ai", "high", "1A", "CC2026001", 912),
    StudentSeed("Leandro Jared Duarte", "leandro.jared@campuscalm.ai", "medium", "1A", "CC2026002", 642),
    StudentSeed("Fernanda Duarte", "fernanda.duarte@campuscalm.ai", "risk", "1A", "CC2026003", 338),
    StudentSeed("Beatriz Silva", "aluno.teste.01@campuscalm.ai", "high", "1A", "CC2026004", 881),
    StudentSeed("Gabriel Oliveira", "aluno.teste.02@campuscalm.ai", "medium", "1A", "CC2026005", 598),
    StudentSeed("Julia Santos", "aluno.teste.03@campuscalm.ai", "high", "1B", "CC2026006", 845),
    StudentSeed("Pedro Henrique Lima", "aluno.teste.04@campuscalm.ai", "high", "1B", "CC2026007", 936),
    StudentSeed("Mariana Costa", "aluno.teste.05@campuscalm.ai", "medium", "1B", "CC2026008", 674),
    StudentSeed("Rafael Alves", "aluno.teste.06@campuscalm.ai", "medium", "1B", "CC2026009", 551),
    StudentSeed("Camila Souza", "aluno.teste.07@campuscalm.ai", "medium", "2A", "CC2026010", 619),
    StudentSeed("Felipe Rocha", "aluno.teste.08@campuscalm.ai", "medium", "2A", "CC2026011", 703),
    StudentSeed("Isabela Martins", "aluno.teste.09@campuscalm.ai", "high", "2A", "CC2026012", 827),
    StudentSeed("Gustavo Ferreira", "aluno.teste.10@campuscalm.ai", "risk", "2A", "CC2026013", 274),
    StudentSeed("Larissa Gomes", "aluno.teste.11@campuscalm.ai", "risk", "2A", "CC2026014", 391),
    StudentSeed("Thiago Barbosa", "aluno.teste.12@campuscalm.ai", "medium", "1A", "CC2026015", 577),
    StudentSeed("Carolina Melo", "aluno.teste.13@campuscalm.ai", "medium", "1B", "CC2026016", 689),
    StudentSeed("Vinicius Araujo", "aluno.teste.14@campuscalm.ai", "risk", "2A", "CC2026017", 243),
    StudentSeed("Bianca Ribeiro", "aluno.teste.15@campuscalm.ai", "risk", "1B", "CC2026018", 362),
]

BAND_RULES = {
    "high": {
        "sessions": (42, 60),
        "tasks": (10, 14),
        "checkins": (8, 14),
        "duration": (35, 60),
        "moods": (
            ("feliz", 3, 10),
            ("motivado", 4, 10),
            ("neutro", 3, 8),
        ),
        "recent_login_gap": (0, 1),
    },
    "medium": {
        "sessions": (20, 34),
        "tasks": (8, 12),
        "checkins": (6, 12),
        "duration": (25, 50),
        "moods": (
            ("motivado", 3, 8),
            ("neutro", 4, 7),
            ("cansado", 5, 6),
        ),
        "recent_login_gap": (1, 4),
    },
    "risk": {
        "sessions": (10, 16),
        "tasks": (6, 10),
        "checkins": (6, 10),
        "duration": (20, 35),
        "moods": (
            ("neutro", 4, 6),
            ("cansado", 6, 5),
            ("ansioso", 7, 4),
        ),
        "recent_login_gap": (5, 12),
    },
}


def log(message: str) -> None:
    print(f"[CampusCalm Seed] {message}")


def aware_at(day_offset: int, hour: int, minute: int) -> datetime:
    target_day = TODAY - timedelta(days=day_offset)
    return timezone.make_aware(datetime.combine(target_day, time(hour=hour, minute=minute)))


def ensure_plan() -> Plan:
    log("Criando/atualizando plano PRO...")
    plan, _ = Plan.objects.update_or_create(
        code=PLAN_PRO,
        defaults={
            "name": "Pro",
            "description": "Plano completo institucional para testes integrados do CampusCalm.",
            "price": Decimal("799.00"),
            "max_students": 2000,
            "features": Plan.default_pro_features(),
            "is_active": True,
        },
    )
    return plan


def ensure_institution(plan: Plan) -> Institution:
    log("Criando instituicao de teste...")
    institution, _ = Institution.objects.update_or_create(
        institution_code=INSTITUTION_CODE,
        defaults={
            "razao_social": "Algorithm Insights Sistemas Educacionais LTDA",
            "nome_fantasia": "CampusCalm Academy",
            "cnpj": "",
            "slug": INSTITUTION_SLUG,
            "website_url": "https://campuscalm.ai",
            "endereco": "Ambiente de testes CampusCalm",
            "cidade": "Fortaleza",
            "estado": "CE",
            "telefone": "",
            "email": "contato@campuscalm.ai",
            "ativa": True,
            "is_pilot": False,
        },
    )
    InstitutionSubscription.objects.filter(institution=institution).delete()
    InstitutionSubscription.objects.create(
        institution=institution,
        plan=plan,
        start_date=TODAY - timedelta(days=30),
        end_date=TODAY + timedelta(days=365 * 3),
        status=InstitutionSubscription.STATUS_ACTIVE,
        is_trial=False,
        notes="Seed de teste para dashboards e study assistant.",
    )
    return institution


def upsert_user(email: str, name: str, role: str, institution: Institution, plan: Plan, *, is_staff: bool = False):
    User = get_user_model()
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "name": name,
            "role": role,
            "institution": institution,
            "preferred_language": User.LANGUAGE_PT_BR,
            "is_active": True,
            "is_staff": is_staff,
        },
    )
    user.name = name
    user.role = role
    user.institution = institution
    user.preferred_language = User.LANGUAGE_PT_BR
    user.is_active = True
    user.is_staff = is_staff
    user.set_password(PASSWORD)
    user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.plan = UserProfile.PLAN_PRO
    profile.coach_enabled = True
    profile.allow_email = True
    profile.allow_whatsapp = True
    profile.allow_sms = False
    profile.save(update_fields=["plan", "coach_enabled", "allow_email", "allow_whatsapp", "allow_sms"])

    UserSubscription.objects.update_or_create(
        user=user,
        defaults={"plan": plan, "is_active": True},
    )
    if created:
        log(f"Usuario criado: {email}")
    return user


def clear_previous_institution_data(institution: Institution) -> None:
    log("Limpando dados pedagogicos anteriores da instituicao de teste...")
    Achievement.objects.filter(institution=institution).delete()
    AcademicDisciplineScore.objects.filter(institution=institution).delete()
    StudyTask.objects.filter(institution=institution).delete()
    StudySession.objects.filter(institution=institution).delete()
    EmotionalCheckin.objects.filter(institution=institution).delete()
    ParentProfile.objects.filter(institution=institution).delete()
    StudentProfile.objects.filter(institution=institution).delete()


def create_student_profiles(student_users: dict[str, object], institution: Institution) -> dict[str, StudentProfile]:
    log("Criando perfis de alunos...")
    profiles = [
        StudentProfile(
            user=student_users[student.email],
            institution=institution,
            enrollment_number=student.enrollment_number,
            grade_level="Ensino Medio",
            class_group=student.class_group,
            status=StudentProfile.STATUS_ACTIVE,
            account_type=StudentProfile.ACCOUNT_INSTITUTIONAL,
        )
        for student in STUDENTS
    ]
    StudentProfile.objects.bulk_create(profiles)
    return {
        profile.user.email: profile
        for profile in StudentProfile.objects.filter(institution=institution).select_related("user")
    }


def create_parent_links(parent_user, student_profiles: dict[str, StudentProfile], institution: Institution) -> None:
    log("Criando vinculo de responsavel para cobrir o dashboard de pais...")
    ParentProfile.objects.bulk_create(
        [
            ParentProfile(
                user=parent_user,
                student=student_profiles["ana.luisa@campuscalm.ai"],
                relationship_type=ParentProfile.RELATION_MOTHER,
                institution=institution,
            ),
            ParentProfile(
                user=parent_user,
                student=student_profiles["leandro.jared@campuscalm.ai"],
                relationship_type=ParentProfile.RELATION_MOTHER,
                institution=institution,
            ),
        ]
    )


def generate_score_values(seed: StudentSeed) -> list[int]:
    target = seed.target_score
    if seed.band == "high":
        raw_values = [target - 120, target - 95, target - 60, target - 40, target - 15, target]
    elif seed.band == "medium":
        raw_values = [target - 70, target - 40, target - 25, target - 10, target + 8, target]
    else:
        raw_values = [target + 110, target + 75, target + 40, target + 15, target - 10, target]
    return [max(0, min(1000, value)) for value in raw_values]


def generate_sessions(student_user, institution: Institution, band: str) -> list[StudySession]:
    rules = BAND_RULES[band]
    total = RNG.randint(*rules["sessions"])
    base_days = set()
    if band == "high":
        base_days.update(range(0, 8))
        base_days.update(RNG.sample(range(8, 45), k=RNG.randint(16, 22)))
    elif band == "medium":
        base_days.update({1, 3, 5, 8})
        base_days.update(RNG.sample(range(9, 45), k=RNG.randint(10, 14)))
    else:
        base_days.update({2, 7})
        base_days.update(RNG.sample(range(10, 45), k=RNG.randint(4, 7)))

    study_days = sorted(base_days)
    sessions: list[StudySession] = []
    for _ in range(total):
        day_offset = RNG.choice(study_days)
        created_at = aware_at(day_offset, RNG.randint(7, 20), RNG.choice((0, 10, 20, 30, 40, 50)))
        sessions.append(
            StudySession(
                student=student_user,
                institution=institution,
                subject=RNG.choice(SUBJECTS),
                duration_minutes=RNG.randint(*rules["duration"]),
                notes=f"Sessao de estudo guiada para {RNG.choice(SUBJECTS)}.",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    sessions.sort(key=lambda item: item.created_at)
    return sessions


def generate_tasks(student_user, institution: Institution, band: str) -> list[StudyTask]:
    rules = BAND_RULES[band]
    total = RNG.randint(*rules["tasks"])
    tasks: list[StudyTask] = []
    for index in range(total):
        due_shift = 25 - index * 3
        due_date = TODAY - timedelta(days=max(-7, due_shift))
        title = TASK_TEMPLATES[index % len(TASK_TEMPLATES)]
        if band == "high":
            completed = index < total - 2
            completed_at = aware_at(max(0, due_shift - RNG.randint(0, 2)), 18, RNG.choice((0, 15, 30))) if completed else None
            if completed and completed_at.date() > due_date:
                completed_at = timezone.make_aware(datetime.combine(due_date, time(17, 0)))
        elif band == "medium":
            completed = index < total - 3
            if completed:
                completed_at = aware_at(max(0, due_shift - RNG.randint(-1, 3)), 19, RNG.choice((0, 20, 40)))
            else:
                completed_at = None
        else:
            completed = index < max(2, total // 3)
            if completed:
                completed_at = aware_at(max(0, due_shift - RNG.randint(-2, 5)), 20, RNG.choice((0, 20, 40)))
            else:
                completed_at = None
        tasks.append(
            StudyTask(
                student=student_user,
                institution=institution,
                title=title,
                description=f"Atividade de estudo orientada de {RNG.choice(SUBJECTS)}.",
                due_date=due_date,
                completed=completed,
                completed_at=completed_at,
                created_at=aware_at(min(44, max(0, due_shift + 4)), 9, RNG.choice((0, 15, 30))),
                updated_at=NOW,
            )
        )
    return tasks


def generate_checkins(student_user, institution: Institution, band: str) -> list[EmotionalCheckin]:
    rules = BAND_RULES[band]
    total = RNG.randint(*rules["checkins"])
    checkins: list[EmotionalCheckin] = []
    for _ in range(total):
        mood, stress_level, motivation_level = RNG.choice(rules["moods"])
        day_offset = RNG.randint(0, 35)
        created_at = aware_at(day_offset, RNG.randint(6, 21), RNG.choice((0, 15, 30, 45)))
        checkins.append(
            EmotionalCheckin(
                student=student_user,
                institution=institution,
                mood=mood,
                stress_level=stress_level,
                motivation_level=motivation_level,
                notes=f"Check-in emocional registrado como {mood}.",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    checkins.sort(key=lambda item: item.created_at)
    return checkins


def generate_scores(student_user, institution: Institution, seed: StudentSeed) -> list[AcademicDisciplineScore]:
    scores: list[AcademicDisciplineScore] = []
    for index, score_value in enumerate(generate_score_values(seed)):
        calculated_at = aware_at(35 - index * 7, 8, 0)
        scores.append(
            AcademicDisciplineScore(
                student=student_user,
                institution=institution,
                score_value=score_value,
                classification=classify_score(score_value),
                calculated_at=calculated_at,
            )
        )
    return scores


def generate_achievements(student_user, institution: Institution, seed: StudentSeed) -> list[Achievement]:
    unlocked_at = aware_at(3, 10, 0)
    achievements: list[Achievement] = []
    if seed.band == "high":
        achievements.extend(
            [
                Achievement(
                    student=student_user,
                    institution=institution,
                    achievement_type=Achievement.ACHIEVEMENT_CONSISTENCY_7_DAYS,
                    title="Primeira semana consistente",
                    description="Sete dias seguidos com estudo ativo e rotina estavel.",
                    unlocked_at=unlocked_at,
                ),
                Achievement(
                    student=student_user,
                    institution=institution,
                    achievement_type=Achievement.ACHIEVEMENT_TASKS_10,
                    title="10 sessoes de estudo",
                    description="Atingiu marca forte de constancia nas atividades do CampusCalm.",
                    unlocked_at=unlocked_at + timedelta(hours=1),
                ),
                Achievement(
                    student=student_user,
                    institution=institution,
                    achievement_type=Achievement.ACHIEVEMENT_STUDY_30H,
                    title="1000 minutos de estudo",
                    description="Acumulou um volume expressivo de estudo ao longo do mes.",
                    unlocked_at=unlocked_at + timedelta(hours=2),
                ),
            ]
        )
        if seed.target_score >= 800:
            achievements.append(
                Achievement(
                    student=student_user,
                    institution=institution,
                    achievement_type=Achievement.ACHIEVEMENT_SCORE_800,
                    title="Melhor disciplina do mes",
                    description="Fechou o periodo com score de disciplina academica acima de 800.",
                    unlocked_at=unlocked_at + timedelta(hours=3),
                )
            )
    elif seed.band == "medium":
        achievements.append(
            Achievement(
                student=student_user,
                institution=institution,
                achievement_type=Achievement.ACHIEVEMENT_TASKS_10,
                title="10 sessoes de estudo",
                description="Manteve uma boa base de constancia nas tarefas da semana.",
                unlocked_at=unlocked_at,
            )
        )
    return achievements


def generate_learning_data(student_users: dict[str, object], institution: Institution) -> None:
    log("Gerando sessoes de estudo...")
    sessions: list[StudySession] = []
    tasks: list[StudyTask] = []
    checkins: list[EmotionalCheckin] = []
    scores: list[AcademicDisciplineScore] = []
    achievements: list[Achievement] = []

    for student in STUDENTS:
        student_user = student_users[student.email]
        rules = BAND_RULES[student.band]
        student_user.last_login = NOW - timedelta(days=RNG.randint(*rules["recent_login_gap"]))
        student_user.save(update_fields=["last_login"])

        sessions.extend(generate_sessions(student_user, institution, student.band))
        tasks.extend(generate_tasks(student_user, institution, student.band))
        checkins.extend(generate_checkins(student_user, institution, student.band))
        scores.extend(generate_scores(student_user, institution, student))
        achievements.extend(generate_achievements(student_user, institution, student))

    StudySession.objects.bulk_create(sessions, batch_size=500)
    log(f"Sessoes criadas: {len(sessions)}")
    StudyTask.objects.bulk_create(tasks, batch_size=500)
    log(f"Tarefas criadas: {len(tasks)}")
    EmotionalCheckin.objects.bulk_create(checkins, batch_size=500)
    log(f"Check-ins criados: {len(checkins)}")
    AcademicDisciplineScore.objects.bulk_create(scores, batch_size=500)
    log(f"Scores criados: {len(scores)}")
    Achievement.objects.bulk_create(achievements, batch_size=200)
    log(f"Achievements criados: {len(achievements)}")


def build_student_users(institution: Institution, plan: Plan) -> dict[str, object]:
    student_users = {}
    for student in STUDENTS:
        student_users[student.email] = upsert_user(
            email=student.email,
            name=student.name,
            role=get_user_model().ROLE_STUDENT,
            institution=institution,
            plan=plan,
        )
    return student_users


def main() -> None:
    log("Seed iniciada.")
    log("Mapeamento aplicado: institution_owner -> institution_admin.")
    with transaction.atomic():
        plan = ensure_plan()
        institution = ensure_institution(plan)

        log("Criando usuarios institucionais...")
        owner = upsert_user(
            email="marcos@campuscalm.ai",
            name="Marcos Duarte Oliveira",
            role=get_user_model().ROLE_INSTITUTION_ADMIN,
            institution=institution,
            plan=plan,
            is_staff=True,
        )
        teacher = upsert_user(
            email="edna@campuscalm.ai",
            name="Edna Barbosa",
            role=get_user_model().ROLE_TEACHER,
            institution=institution,
            plan=plan,
        )
        parent = upsert_user(
            email="luciana@campuscalm.ai",
            name="Luciana Duarte",
            role=get_user_model().ROLE_PARENT,
            institution=institution,
            plan=plan,
        )

        owner.last_login = NOW
        teacher.last_login = NOW - timedelta(hours=3)
        parent.last_login = NOW - timedelta(hours=5)
        owner.save(update_fields=["last_login"])
        teacher.save(update_fields=["last_login"])
        parent.save(update_fields=["last_login"])

        clear_previous_institution_data(institution)
        student_users = build_student_users(institution, plan)
        student_profiles = create_student_profiles(student_users, institution)
        create_parent_links(parent, student_profiles, institution)
        generate_learning_data(student_users, institution)

    log("Gerando dashboards pedagogicos...")
    log(f"Instituicao pronta: {institution.nome_fantasia}")
    log(f"Usuarios principais: {owner.email}, {teacher.email}, {parent.email}")
    log(f"Alunos ativos criados: {len(STUDENTS)}")
    log("Seed finalizada com sucesso.")


main()
