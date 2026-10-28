from datetime import date

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.audits.models import AuditMission
from apps.departments.models import Department
from apps.notifications.models import Notification, NotificationDelivery
from apps.recommendations.models import Recommendation, RecommendationHistory
from apps.recommendations.services import RecommendationService, recommendation_scope


class RecommendationServiceTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Finance", code="FIN")
        self.other_department = Department.objects.create(name="Operations", code="OPS")
        self.audit_user = User.objects.create_user(
            username="audit", role=User.Role.AUDIT
        )
        self.manager = User.objects.create_user(
            username="manager",
            role=User.Role.DEPARTMENT_MANAGER,
            department=self.department,
        )
        self.responsible = User.objects.create_user(
            username="responsible",
            role=User.Role.RESPONSIBLE,
            department=self.department,
        )
        self.other_user = User.objects.create_user(
            username="other",
            role=User.Role.VIEWER,
            department=self.other_department,
        )
        self.mission = AuditMission.objects.create(
            mission_name="Annual review",
            audited_entity="Finance",
            issuance_date=date(2026, 10, 28),
        )

    def create_recommendation(self, reference, **kwargs):
        return RecommendationService.create(
            actor=self.audit_user,
            reference=reference,
            audit_mission=self.mission,
            finding="Finding",
            recommendation="Recommendation",
            **kwargs,
        )

    def test_effective_due_date_and_overdue_status_are_computed(self):
        reco = self.create_recommendation(
            "REC-001",
            planned_implementation_date=date(2026, 10, 20),
        )
        self.assertEqual(reco.effective_due_date, date(2026, 10, 20))
        self.assertEqual(reco.computed_status(as_of=date(2026, 10, 28)), "OVERDUE")
        self.assertEqual(reco.status, Recommendation.Status.OPEN)

        RecommendationService.change_due_date(
            recommendation=reco,
            actor=self.audit_user,
            new_date=date(2026, 11, 15),
            reason="Approved extension",
        )
        reco.refresh_from_db()
        self.assertEqual(reco.planned_implementation_date, date(2026, 10, 20))
        self.assertEqual(reco.effective_due_date, date(2026, 11, 15))

    def test_manager_sees_department_and_department_member_recommendations(self):
        by_department = self.create_recommendation(
            "REC-001", responsible_department=self.department
        )
        by_member = self.create_recommendation(
            "REC-002", responsibles=[self.responsible]
        )
        out_of_scope = self.create_recommendation(
            "REC-003", responsible_department=self.other_department
        )

        visible = set(
            recommendation_scope(self.manager).values_list("pk", flat=True)
        )
        self.assertEqual(visible, {by_department.pk, by_member.pk})
        self.assertNotIn(out_of_scope.pk, visible)

    def test_responsible_can_declare_implementation_but_not_close(self):
        reco = self.create_recommendation(
            "REC-001", responsibles=[self.responsible]
        )
        RecommendationService.update_status(
            recommendation=reco,
            actor=self.responsible,
            new_status=Recommendation.Status.IN_PROGRESS,
        )
        RecommendationService.update_status(
            recommendation=reco,
            actor=self.responsible,
            new_status=Recommendation.Status.IMPLEMENTED,
        )
        with self.assertRaises(PermissionDenied):
            RecommendationService.update_status(
                recommendation=reco,
                actor=self.responsible,
                new_status=Recommendation.Status.CLOSED,
            )

        RecommendationService.update_status(
            recommendation=reco,
            actor=self.audit_user,
            new_status=Recommendation.Status.CLOSED,
        )
        reco.refresh_from_db()
        self.assertEqual(reco.status, Recommendation.Status.CLOSED)
        self.assertEqual(reco.closing_date, timezone.localdate())

    def test_viewer_cannot_change_status_and_history_is_immutable(self):
        reco = self.create_recommendation("REC-001")
        with self.assertRaises(PermissionDenied):
            RecommendationService.update_status(
                recommendation=reco,
                actor=self.other_user,
                new_status=Recommendation.Status.IN_PROGRESS,
            )

        entry = reco.history.first()
        entry.comment = "tampered"
        with self.assertRaises(ValidationError):
            entry.save()
        with self.assertRaises(ValidationError):
            entry.delete()

    def test_global_reference_uniqueness(self):
        self.create_recommendation("REC-001")
        with self.assertRaises(IntegrityError):
            self.create_recommendation("REC-001")

    def test_notification_idempotency_key_and_delivery_channel_are_unique(self):
        reco = self.create_recommendation("REC-001")
        notification = Notification.objects.create(
            recommendation=reco,
            recipient=self.responsible,
            notification_type=Notification.Type.DUE_SOON,
            subject="Due soon",
            message="Reminder",
            scheduled_at=timezone.now(),
            deduplication_key="REC-001:due-soon:responsible:2026-11-04",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Notification.objects.create(
                    recommendation=reco,
                    recipient=self.responsible,
                    notification_type=Notification.Type.DUE_SOON,
                    subject="Duplicate",
                    message="Duplicate reminder",
                    scheduled_at=timezone.now(),
                    deduplication_key="REC-001:due-soon:responsible:2026-11-04",
                )

        NotificationDelivery.objects.create(
            notification=notification, channel=NotificationDelivery.Channel.EMAIL
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NotificationDelivery.objects.create(
                    notification=notification,
                    channel=NotificationDelivery.Channel.EMAIL,
                )
