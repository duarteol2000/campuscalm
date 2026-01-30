from utils.academic_progress import (
    calculate_course_average,
    calculate_needed_to_pass,
    calculate_progress_percent,
)


def build_course_progress(course):
    assessments_qs = course.assessments.all()
    has_assessments = assessments_qs.exists()
    current_average = calculate_course_average(course)
    progress_percent = calculate_progress_percent(course)
    needed_to_pass = calculate_needed_to_pass(course)
    return {
        "has_assessments": has_assessments,
        "current_average": current_average,
        "passing_grade": course.passing_grade,
        "progress_percent": progress_percent,
        "needed_to_pass": needed_to_pass,
    }
