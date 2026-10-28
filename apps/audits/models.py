from django.db import models


class AuditMission(models.Model):
    mission_name = models.CharField("nom de la mission", max_length=200)
    source = models.CharField("source", max_length=120, blank=True)
    audited_entity = models.CharField("entité auditée", max_length=200)
    recording_date = models.DateField("date d’enregistrement", blank=True, null=True)
    issuance_date = models.DateField("date d’émission", blank=True, null=True)
    description = models.TextField("description", blank=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField("modifiée le", auto_now=True)

    class Meta:
        ordering = ["-issuance_date", "mission_name"]
        indexes = [models.Index(fields=["issuance_date"], name="audit_issuance_date_idx")]
        verbose_name = "mission d’audit"
        verbose_name_plural = "missions d’audit"

    @property
    def issuance_quarter(self):
        if self.issuance_date is None:
            return ""
        quarter = (self.issuance_date.month - 1) // 3 + 1
        return f"T{quarter} {self.issuance_date.year}"

    def __str__(self):
        return self.mission_name
