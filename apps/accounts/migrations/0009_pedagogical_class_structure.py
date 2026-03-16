from django.db import migrations, models
import django.db.models.deletion


def backfill_class_group_refs(apps, schema_editor):
    StudentProfile = apps.get_model("accounts", "StudentProfile")
    ClassGroup = apps.get_model("accounts", "ClassGroup")

    existing_profiles = StudentProfile.objects.exclude(class_group="").values(
        "institution_id",
        "class_group",
        "grade_level",
    )

    class_groups_to_create = {}
    for row in existing_profiles.iterator():
        key = (
            row["institution_id"],
            row["class_group"],
            row["grade_level"] or "",
        )
        if key not in class_groups_to_create:
            class_groups_to_create[key] = ClassGroup(
                institution_id=row["institution_id"],
                name=row["class_group"],
                grade_level=row["grade_level"] or "",
            )

    if class_groups_to_create:
        ClassGroup.objects.bulk_create(class_groups_to_create.values(), ignore_conflicts=True)

    class_group_map = {
        (class_group.institution_id, class_group.name, class_group.grade_level or ""): class_group.id
        for class_group in ClassGroup.objects.all().iterator()
    }

    profiles_to_update = []
    for profile in StudentProfile.objects.exclude(class_group="").iterator():
        lookup_key = (
            profile.institution_id,
            profile.class_group,
            profile.grade_level or "",
        )
        class_group_id = class_group_map.get(lookup_key)
        if class_group_id and profile.class_group_ref_id != class_group_id:
            profile.class_group_ref_id = class_group_id
            profiles_to_update.append(profile)

    if profiles_to_update:
        StudentProfile.objects.bulk_update(profiles_to_update, ["class_group_ref"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_profile_uniques"),
        ("billing", "0002_institutional_saas_baseline"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("grade_level", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "institution",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="class_groups", to="billing.institution"),
                ),
            ],
            options={
                "ordering": ("grade_level", "name"),
            },
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="class_group_ref",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="students", to="accounts.classgroup"),
        ),
        migrations.CreateModel(
            name="TeacherAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "class_group",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teacher_assignments", to="accounts.classgroup"),
                ),
                (
                    "institution",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teacher_assignments", to="billing.institution"),
                ),
                (
                    "teacher",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="class_assignments", to="accounts.user"),
                ),
            ],
            options={
                "ordering": ("teacher__name", "class_group__grade_level", "class_group__name"),
            },
        ),
        migrations.AddConstraint(
            model_name="classgroup",
            constraint=models.UniqueConstraint(fields=("institution", "name", "grade_level"), name="unique_class_per_institution"),
        ),
        migrations.AddConstraint(
            model_name="teacherassignment",
            constraint=models.UniqueConstraint(fields=("teacher", "class_group"), name="unique_teacher_class_assignment"),
        ),
        migrations.RunPython(backfill_class_group_refs, migrations.RunPython.noop),
    ]
