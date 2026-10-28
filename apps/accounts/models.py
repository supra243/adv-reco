from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrateur"
        AUDIT = "AUDIT", "Audit"
        DEPARTMENT_MANAGER = "DEPARTMENT_MANAGER", "Responsable de département"
        RESPONSIBLE = "RESPONSIBLE", "Responsable de recommandation"
        VIEWER = "VIEWER", "Lecteur"

    department = models.ForeignKey(
        "departments.Department",
        verbose_name="département",
        related_name="users",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    role = models.CharField(
        "rôle",
        max_length=24,
        choices=Role.choices,
        default=Role.VIEWER,
        db_index=True,
    )

    class Meta(AbstractUser.Meta):
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self):
        return self.get_full_name() or self.username
