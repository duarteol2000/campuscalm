from decimal import Decimal, ROUND_HALF_UP


def calculate_course_average(course) -> Decimal:
    assessments = course.assessments.all()
    total_weight = sum((a.weight for a in assessments), Decimal("0"))
    if total_weight == 0:
        return Decimal("0")
    total_score = sum((a.score * a.weight for a in assessments), Decimal("0"))
    return (total_score / total_weight).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_progress_percent(course) -> Decimal:
    current_average = calculate_course_average(course)
    passing_grade = course.passing_grade or Decimal("0")
    if passing_grade == 0:
        return Decimal("0")
    progress = (current_average / passing_grade) * Decimal("100")
    return min(Decimal("100"), progress)


def calculate_needed_to_pass(course) -> Decimal:
    current_average = calculate_course_average(course)
    passing_grade = course.passing_grade or Decimal("0")
    needed = passing_grade - current_average
    return max(Decimal("0"), needed)


def update_course_status(course, semester_status: str | None = None) -> None:
    from utils.constants import COURSE_FAILED, COURSE_IN_PROGRESS, COURSE_PASSED, SEMESTER_FINISHED

    progress = calculate_progress_percent(course)
    if progress >= Decimal("100"):
        course.status = COURSE_PASSED
        return
    if semester_status == SEMESTER_FINISHED:
        course.status = COURSE_FAILED
        return
    course.status = COURSE_IN_PROGRESS
