# Suivi des recommandations d’audit

Application Django destinée à remplacer progressivement le classeur de suivi des
recommandations d’audit.

## Socle métier

- Une référence de recommandation est unique dans toute l’application.
- La mission conserve l’entité auditée ; la recommandation conserve séparément le
  département chargé de sa mise en œuvre.
- Les responsables sont liés à une recommandation par une relation dédiée, qui
  permet plusieurs responsables et un responsable principal.
- L’échéance effective est la date révisée si elle existe, sinon la date initiale.
- `IMPLEMENTED` correspond à la déclaration de mise en œuvre ; seul l’audit peut
  passer une recommandation à `CLOSED`.
- `OVERDUE` est un état calculé et ne remplace jamais le statut déclaré.
- Les trimestres sont dérivés des dates d’émission et de clôture.
- Les notifications et leurs envois par canal disposent d’une clé d’idempotence
  unique, afin que le moteur asynchrone puisse éviter les doublons.

Les services du domaine se trouvent dans
[`apps/recommendations/services/`](apps/recommendations/services/). Ils contrôlent
les transitions et enregistrent les changements dans l’historique. Les rôles
`DEPARTMENT_MANAGER` et `VIEWER` sont limités aux recommandations du département
de l’utilisateur, tandis que `AUDIT` a un accès global.

Les modèles de notifications sont dans
[`apps/notifications/models.py`](apps/notifications/models.py). La planification
Celery, les envois email et les opérations HTMX seront ajoutés dans les étapes
suivantes.

## Démarrage local du socle

Prérequis : Python 3.13 et PostgreSQL 15+ (SQLite est disponible pour le
développement et les tests locaux).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Le serveur d’administration est disponible à `/admin/`. Le démarrage local
utilise les paramètres `config.settings.development` et SQLite par défaut.
Pour PostgreSQL, définir `DATABASE_URL`, par exemple :

```text
postgresql://adv_reco:mot_de_passe@localhost:5432/adv_reco
```

En production, définir au minimum `DJANGO_SETTINGS_MODULE=config.settings.production`,
`SECRET_KEY`, `DATABASE_URL` et `ALLOWED_HOSTS`. Ne pas utiliser la clé de
développement hors d’un poste local.