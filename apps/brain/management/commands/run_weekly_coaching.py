import logging

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from accounts.models import User
from brain.models import WeeklyCoachingAssessment
from brain.services.coaching_service import calculate_weekly_score, is_coaching_eligible, send_coaching_email

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Executa avaliacao semanal de coaching e envia email proativo (quando aplicavel)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-eligible",
            action="store_true",
            help="Processa apenas usuarios PRO ou com coach_enabled=True.",
        )
        parser.add_argument(
            "--user-email",
            dest="user_email",
            help="Processa somente um usuario (email) para teste.",
        )

    def handle(self, *args, **options):
        only_eligible = bool(options.get("only_eligible"))
        user_email = (options.get("user_email") or "").strip()

        users_qs = User.objects.filter(is_active=True).order_by("id")
        if user_email:
            users_qs = users_qs.filter(email__iexact=user_email)

        processed = 0
        created = 0
        emailed = 0
        skipped_existing = 0
        skipped_not_eligible = 0
        errors = 0

        for user in users_qs.iterator():
            processed += 1
            if not is_coaching_eligible(user, allow_all=not only_eligible):
                skipped_not_eligible += 1
                self.stdout.write(f"[SKIP] {user.email} - not eligible")
                continue

            try:
                result = calculate_weekly_score(user)
                assessment, was_created = WeeklyCoachingAssessment.objects.get_or_create(
                    user=user,
                    week_reference=result.week_reference,
                    defaults={
                        "score": result.score,
                        "risk_level": result.risk_level,
                    },
                )
                if not was_created:
                    skipped_existing += 1
                    self.stdout.write(
                        f"[SKIP] {user.email} - semana {result.week_reference} ja processada ({assessment.risk_level})"
                    )
                    continue

                created += 1

                if result.risk_level != WeeklyCoachingAssessment.RISK_STABLE and user.email:
                    try:
                        send_coaching_email(user, result.risk_level)
                    except Exception as exc:  # noqa: BLE001 - nao interromper lote por falha individual
                        errors += 1
                        logger.exception(
                            "weekly_coaching_email_failed user_id=%s week=%s",
                            user.id,
                            result.week_reference,
                        )
                        self.stderr.write(f"[ERRO EMAIL] {user.email}: {exc}")
                    else:
                        assessment.email_sent = True
                        assessment.save(update_fields=["email_sent"])
                        emailed += 1

                self.stdout.write(
                    f"[OK] {user.email} - week={result.week_reference} score={result.score} risk={result.risk_level} email_sent={assessment.email_sent}"
                )
            except IntegrityError:
                skipped_existing += 1
                self.stdout.write(f"[SKIP] {user.email} - registro duplicado detectado")
            except Exception as exc:  # noqa: BLE001 - nao interromper lote por falha individual
                errors += 1
                logger.exception("weekly_coaching_processing_failed user_id=%s", user.id)
                self.stderr.write(f"[ERRO] {user.email}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                "\n".join(
                    [
                        "Resumo run_weekly_coaching",
                        f"- usuarios avaliados: {processed}",
                        f"- registros criados: {created}",
                        f"- emails enviados: {emailed}",
                        f"- pulados: {skipped_existing + skipped_not_eligible}",
                        f"  - ja processados na semana: {skipped_existing}",
                        f"  - nao elegiveis: {skipped_not_eligible}",
                        f"- falhas: {errors}",
                        (
                            "  [detalhe] "
                            f"processed={processed} created={created} emailed={emailed} "
                            f"skipped_existing={skipped_existing} skipped_not_eligible={skipped_not_eligible} errors={errors}"
                        ),
                    ]
                )
            )
        )
