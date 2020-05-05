from rest_framework import status

from api.common.auth import get_role


def role_required(allowed_roles=[]):
    def decorator(view_func):
        def wrap(request, *args, **kwargs):
            role = get_role(request)

            if role.role_code in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                return Response(
                    {"message": "Permission required!"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return wrap

    return decorator


def admin_only(view_func):
    def wrap(request, *args, **kwargs):
        role = get_role(request)

        if role.role_code == "admin":
            return view_func(request, *args, **kwargs)
        else:
            return Response(
                {"message": "Permission required!"}, status=status.HTTP_403_FORBIDDEN
            )

    return wrap
