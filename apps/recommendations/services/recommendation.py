from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.recommendations.models import (
    DueDateChange,
    Recommendation,
    RecommendationHistory,
    RecommendationResponsible,
)


_AUDIT_ROLES = {User.Role.ADMIN, User.Role.AUDIT}
_ALLOWED_TRANSITIONS = {
    Recommendation.Status.OPEN: {
        Recommendation.Status.IN_PROGRESS,
        Recommendation.Status.IMPLEMENTED,
        Recommendation.Status.CANCELLED,
    },
    Recommendation.Status.IN_PROGRESS: {
        Recommendation.Status.OPEN,
        Recommendation.Status.IMPLEMENTED,
        Recommendation.Status.CANCELLED,
    },
    Recommendation.Status.IMPLEMENTED: {
        Recommendation.Status.IN_PROGRESS,
        Recommendation.Status.CLOSED,
        Recommendation.Status.CANCELLED,
    },
    Recommendation.Status.CLOSED: {Recommendation.Status.IN_PROGRESS},
    Recommendation.Status.CANCELLED: {Recommendation.Status.OPEN},
}


def _is_global_auditor(user):
    return user.is_authenticated and (
        user.is_superuser or user.role in _AUDIT_ROLES
    )


def _require_audit(user):
    if not _is_global_auditor(user):
        raise PermissionDenied("Cette opération est réservée à l’équipe d’audit.")


def _record_history(recommendation, actor, action, field="", old=None, new=None, comment=""):
    RecommendationHistory.objects.create(
        recommendation=recommendation,
        user=actor,
        action=action,
        field=field,
        old_value=old,
        new_value=new,
        comment=comment,
    )


def recommendation_scope(user):
    queryset = Recommendation.objects.all()
    if not user.is_authenticated or not user.is_active:
        return queryset.none()
    if _is_global_auditor(user):
        return queryset

    if user.role in {User.Role.DEPARTMENT_MANAGER, User.Role.VIEWER}:
        if user.department_id is None:
            return queryset.none()
        return queryset.filter(
            Q(responsible_department_id=user.department_id)
            | Q(responsibles__user__department_id=user.department_id)
        ).distinct()
    if user.role == User.Role.RESPONSIBLE:
        return queryset.filter(responsibles__user=user).distinct()
    return queryset.none()


class RecommendationService:
    @staticmethod
    @transaction.atomic
    def create(*, actor, responsibles=(), primary_responsible=None, **fields):
        _require_audit(actor)
        recommendation = Recommendation.objects.create(created_by=actor, **fields)
        _record_history(
            recommendation,
            actor,
            RecommendationHistory.Action.CREATED,
            new={"reference": recommendation.reference},
        )
        if primary_responsible is not None and primary_responsible not in responsibles:
            responsibles = [*responsibles, primary_responsible]
        RecommendationService.set_responsibles(
            recommendation=recommendation,
            actor=actor,
            users=responsibles,
            primary_user=primary_responsible,
        )
        return recommendation

    @staticmethod
    @transaction.atomic
    def set_responsibles(*, recommendation, actor, users, primary_user=None):
        _require_audit(actor)
        users = list(dict.fromkeys(users))
        if primary_user is not None and primary_user not in users:
            raise ValidationError("Le responsable principal doit faire partie des responsables.")
        if any(not user.is_active for user in users):
            raise ValidationError("Un utilisateur inactif ne peut pas être affecté.")

        old_users = list(
            recommendation.responsibles.select_related("user").values_list(
                "user__username", flat=True
            )
        )
        recommendation.responsibles.all().delete()
        RecommendationResponsible.objects.bulk_create(
            [
                RecommendationResponsible(
                    recommendation=recommendation,
                    user=user,
                    is_primary=(user == primary_user),
                )
                for user in users
            ]
        )
        new_users = [user.username for user in users]
        if old_users != new_users:
            _record_history(
                recommendation,
                actor,
                RecommendationHistory.Action.ASSIGNED,
                field="responsibles",
                old=old_users,
                new=new_users,
            )
        recommendation.updated_by = actor
        recommendation.save(update_fields=["updated_by", "updated_at"])

    @staticmethod
    @transaction.atomic
    def update_status(*, recommendation, actor, new_status, comment=""):
        if new_status not in Recommendation.Status.values:
            raise ValidationError({"status": "Statut inconnu."})
        if not actor.is_authenticated or not actor.is_active:
            raise PermissionDenied

        is_audit = _is_global_auditor(actor)
        if not is_audit:
            assigned = recommendation.responsibles.filter(user=actor).exists()
            if not assigned:
                raise PermissionDenied("Cette recommandation ne vous est pas attribuée.")
            if new_status not in {
                Recommendation.Status.IN_PROGRESS,
                Recommendation.Status.IMPLEMENTED,
            }:
                raise PermissionDenied("Vous ne pouvez pas effectuer cette transition.")
        if new_status not in _ALLOWED_TRANSITIONS[recommendation.status]:
            raise ValidationError(
                {"status": f"Transition interdite : {recommendation.status} → {new_status}."}
            )
        if new_status == Recommendation.Status.CLOSED and not is_audit:
            raise PermissionDenied("Seule l’équipe d’audit peut clôturer une recommandation.")

        old_status = recommendation.status
        recommendation.status = new_status
        if new_status == Recommendation.Status.CLOSED:
            recommendation.closing_date = timezone.localdate()
            action = RecommendationHistory.Action.CLOSED
        elif old_status == Recommendation.Status.CLOSED:
            recommendation.closing_date = None
            action = RecommendationHistory.Action.REOPENED
        else:
            action = RecommendationHistory.Action.STATUS_CHANGED
        recommendation.updated_by = actor
        recommendation.save(
            update_fields=["status", "closing_date", "updated_by", "updated_at"]
        )
        _record_history(
            recommendation,
            actor,
            action,
            field="status",
            old=old_status,
            new=new_status,
            comment=comment,
        )
        return recommendation

    @staticmethod
    @transaction.atomic
    def change_due_date(*, recommendation, actor, new_date, reason):
        _require_audit(actor)
        if not reason.strip():
            raise ValidationError({"reason": "Le motif du changement est obligatoire."})
        previous_date = recommendation.effective_due_date
        if new_date == previous_date:
            raise ValidationError({"new_date": "La nouvelle échéance est identique à l’actuelle."})
        DueDateChange.objects.create(
            recommendation=recommendation,
            previous_date=previous_date,
            new_date=new_date,
            reason=reason.strip(),
            changed_by=actor,
        )
        recommendation.updated_implementation_date = new_date
        recommendation.updated_by = actor
        recommendation.save(
            update_fields=["updated_implementation_date", "updated_by", "updated_at"]
        )
        _record_history(
            recommendation,
            actor,
            RecommendationHistory.Action.DUE_DATE_CHANGED,
            field="effective_due_date",
            old=previous_date.isoformat() if previous_date else None,
            new=new_date.isoformat(),
            comment=reason.strip(),
        )
        return recommendation
