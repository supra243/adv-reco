from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        ASSIGNMENT = "ASSIGNMENT", "Nouvelle attribution"
        DUE_SOON = "DUE_SOON", "Échéance à venir"
        DUE_TODAY = "DUE_TODAY", "Échéance aujourd’hui"
        OVERDUE = "OVERDUE", "Recommandation en retard"

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        SENT = "SENT", "Envoyée"
        FAILED = "FAILED", "Échec"

    recommendation = models.ForeignKey(
        "recommendations.Recommendation",
        related_name="notifications",
        on_delete=models.PROTECT,
    )
    recipient = models.ForeignKey(
        "accounts.User",
        related_name="notifications",
        on_delete=models.PROTECT,
    )
    notification_type = models.CharField(
        "type", max_length=16, choices=Type.choices, db_index=True
    )
    subject = models.CharField("objet", max_length=250)
    message = models.TextField("message")
    scheduled_at = models.DateTimeField("prévue le", db_index=True)
    sent_at = models.DateTimeField("envoyée le", blank=True, null=True)
    status = models.CharField(
        "statut",
        max_length=8,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    retry_count = models.PositiveSmallIntegerField("nombre de tentatives", default=0)
    error_message = models.TextField("erreur", blank=True)
    deduplication_key = models.CharField("clé d’idempotence", max_length=200, unique=True)
    due_date_reference = models.DateField("échéance concernée", blank=True, null=True)
    read_at = models.DateTimeField("lue le", blank=True, null=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient", "read_at", "created_at"],
                name="notif_recipient_read_idx",
            ),
            models.Index(
                fields=["status", "scheduled_at"],
                name="notif_status_schedule_idx",
            ),
        ]
        verbose_name = "notification"
        verbose_name_plural = "notifications"

    def __str__(self):
        return f"{self.get_notification_type_display()} — {self.recipient}"


class NotificationDelivery(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        SENT = "SENT", "Envoyée"
        FAILED = "FAILED", "Échec"

    notification = models.ForeignKey(
        Notification, related_name="deliveries", on_delete=models.PROTECT
    )
    channel = models.CharField("canal", max_length=12, choices=Channel.choices)
    status = models.CharField(
        "statut",
        max_length=8,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    retry_count = models.PositiveSmallIntegerField("nombre de tentatives", default=0)
    sent_at = models.DateTimeField("envoyée le", blank=True, null=True)
    error_message = models.TextField("erreur", blank=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "channel"],
                name="unique_notification_delivery_channel",
            )
        ]
        verbose_name = "envoi de notification"
        verbose_name_plural = "envois de notifications"

    def __str__(self):
        return f"{self.channel} — {self.notification}"
