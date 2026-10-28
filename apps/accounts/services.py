def has_global_access(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.role in {user.Role.ADMIN, user.Role.AUDIT}
    )
