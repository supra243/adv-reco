from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Recommendation(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Ouverte"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        IMPLEMENTED = "IMPLEMENTED", "Mise en œuvre déclarée"
        CLOSED = "CLOSED", "Clôturée"
        CANCELLED = "CANCELLED", "Annulée"

    reference = models.CharField("référence", max_length=60, unique=True)
    audit_mission = models.ForeignKey(
        "audits.AuditMission",
        verbose_name="mission d’audit",
        related_name="recommendations",
        on_delete=models.PROTECT,
    )
    finding = models.TextField("constat")
    recommendation = models.TextField("recommandation")
    deficiency_type = models.CharField("type de déficience", max_length=120, blank=True)
    risk_type = models.CharField("type de risque", max_length=120, blank=True, db_index=True)
    macro_process = models.CharField("macro-processus", max_length=150, blank=True)
    activity = models.CharField("activité", max_length=150, blank=True)
    classification = models.CharField("classification", max_length=120, blank=True, db_index=True)
    expected_deliverables = models.TextField("livrables attendus", blank=True)
    responsible_department = models.ForeignKey(
        "departments.Department",
        verbose_name="département chargé de la mise en œuvre",
        related_name="recommendations",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    network_branch = models.CharField("agence du réseau", max_length=150, blank=True)
    planned_implementation_date = models.DateField(
        "date de mise en œuvre initialement prévue", blank=True, null=True
    )
    updated_implementation_date = models.DateField(
        "date de mise en œuvre révisée", blank=True, null=True
    )
    closing_date = models.DateField("date de clôture", blank=True, null=True)
    status = models.CharField(
        "statut déclaré",
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    audit_comments = models.TextField("commentaires d’audit", blank=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("modifiée le", auto_now=True)
    created_by = models.ForeignKey(
        "accounts.User",
        verbose_name="créée par",
        related_name="created_recommendations",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        verbose_name="modifiée par",
        related_name="updated_recommendations",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["reference"]
        indexes = [
            models.Index(
                fields=["responsible_department", "status"],
                name="reco_dept_status_idx",
            ),
            models.Index(
                fields=["planned_implementation_date"],
                name="reco_planned_date_idx",
            ),
            models.Index(
                fields=["updated_implementation_date"],
                name="reco_updated_date_idx",
            ),
        ]
        verbose_name = "recommandation"
        verbose_name_plural = "recommandations"

    @property
    def effective_due_date(self):
        return self.updated_implementation_date or self.planned_implementation_date

    def computed_status(self, as_of=None):
        as_of = as_of or timezone.localdate()
        if (
            self.effective_due_date is not None
            and self.effective_due_date < as_of
            and self.status not in {self.Status.CLOSED, self.Status.CANCELLED}
        ):
            return "OVERDUE"
        return self.status

    @property
    def closing_quarter(self):
        if self.closing_date is None:
            return ""
        quarter = (self.closing_date.month - 1) // 3 + 1
        return f"T{quarter} {self.closing_date.year}"

    def __str__(self):
        return self.reference


class RecommendationResponsible(models.Model):
    class ResponsibilityRole(models.TextChoices):
        RESPONSIBLE = "RESPONSIBLE", "Responsable"
        CONTRIBUTOR = "CONTRIBUTOR", "Contributeur"

    recommendation = models.ForeignKey(
        Recommendation, related_name="responsibles", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        "accounts.User", related_name="recommendation_assignments", on_delete=models.PROTECT
    )
    role = models.CharField(
        "rôle dans la recommandation",
        max_length=16,
        choices=ResponsibilityRole.choices,
        default=ResponsibilityRole.RESPONSIBLE,
    )
    is_primary = models.BooleanField("responsable principal", default=False)
    assigned_at = models.DateTimeField("attribué le", auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "user__last_name", "user__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["recommendation", "user"],
                name="unique_recommendation_responsible",
            ),
            models.UniqueConstraint(
                fields=["recommendation"],
                condition=Q(is_primary=True),
                name="unique_primary_reco_responsible",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "recommendation"], name="reco_resp_user_idx")
        ]
        verbose_name = "responsable de recommandation"
        verbose_name_plural = "responsables de recommandation"

    def __str__(self):
        return f"{self.user} — {self.recommendation.reference}"


class RecommendationHistory(models.Model):
    class Action(models.TextChoices):
        CREATED = "CREATED", "Création"
        UPDATED = "UPDATED", "Modification"
        STATUS_CHANGED = "STATUS_CHANGED", "Changement de statut"
        ASSIGNED = "ASSIGNED", "Attribution"
        DUE_DATE_CHANGED = "DUE_DATE_CHANGED", "Changement d’échéance"
        CLOSED = "CLOSED", "Clôture"
        REOPENED = "REOPENED", "Réouverture"
        COMMENTED = "COMMENTED", "Commentaire"

    recommendation = models.ForeignKey(
        Recommendation, related_name="history", on_delete=models.PROTECT
    )
    user = models.ForeignKey(
        "accounts.User",
        verbose_name="utilisateur",
        related_name="recommendation_history",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    action = models.CharField("action", max_length=20, choices=Action.choices)
    field = models.CharField("champ", max_length=80, blank=True)
    old_value = models.JSONField("ancienne valeur", blank=True, null=True)
    new_value = models.JSONField("nouvelle valeur", blank=True, null=True)
    comment = models.TextField("commentaire", blank=True)
    timestamp = models.DateTimeField("date", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp", "-pk"]
        verbose_name = "entrée d’historique"
        verbose_name_plural = "historique"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("L’historique d’une recommandation est immuable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("L’historique d’une recommandation ne peut pas être supprimé.")

    def __str__(self):
        return f"{self.recommendation.reference} — {self.get_action_display()}"


class DueDateChange(models.Model):
    recommendation = models.ForeignKey(
        Recommendation, related_name="due_date_changes", on_delete=models.PROTECT
    )
    previous_date = models.DateField("échéance précédente", blank=True, null=True)
    new_date = models.DateField("nouvelle échéance")
    reason = models.TextField("motif")
    changed_by = models.ForeignKey(
        "accounts.User",
        verbose_name="modifiée par",
        related_name="due_date_changes",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    changed_at = models.DateTimeField("modifiée le", auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "modification d’échéance"
        verbose_name_plural = "modifications d’échéance"

    def __str__(self):
        return f"{self.recommendation.reference} — {self.new_date}"


class RecommendationComment(models.Model):
    recommendation = models.ForeignKey(
        Recommendation, related_name="follow_up_comments", on_delete=models.PROTECT
    )
    author = models.ForeignKey(
        "accounts.User",
        verbose_name="auteur",
        related_name="recommendation_comments",
        on_delete=models.PROTECT,
    )
    body = models.TextField("commentaire")
    created_at = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "commentaire de suivi"
        verbose_name_plural = "commentaires de suivi"

    def __str__(self):
        return f"{self.recommendation.reference} — {self.author}"
