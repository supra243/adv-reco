from django.db import models


class Department(models.Model):
    name = models.CharField("nom", max_length=150, unique=True)
    code = models.CharField("code", max_length=30, unique=True)
    description = models.TextField("description", blank=True)
    is_active = models.BooleanField("actif", default=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "département"
        verbose_name_plural = "départements"

    def __str__(self):
        return f"{self.code} — {self.name}"
