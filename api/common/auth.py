from api.models import *


def get_username(user):
    return user.username


def get_client(user):
    client_employees = Client_employees.objects.filter(fk_id_user=user)

    if client_employees:
        client = DME_clients.objects.get(
            pk_id_dme_client=client_employees.first().fk_id_dme_client_id
        )
        return client
    else:
        return None


def get_user_role(user):
    dme_employees = DME_employees.objects.filter(fk_id_user=user)

    if dme_employees:
        return dme_employees.first().get_role()
    else:
        client_employees = Client_employees.objects.filter(fk_id_user=user)

        if client_employees:
            return client_employees.first().get_role()
