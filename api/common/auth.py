from api.models import DME_clients, DME_employees, Client_employees


def get_role(request):
    user_id = request.user.id
    dme_employee = (
        DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
    )

    if dme_employee:
        return dme_employee.role
    else:
        client_employee = (
            Client_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )
        return client_employee.role


def get_client_info(request):
    user_id = request.user.id
    dme_employee = (
        DME_employees.objects.select_related().filter(fk_id_user=user_id).first()
    )

    if dme_employee:
        return {
            "username": request.user.username,
            "clientname": "dme",
            "client_id": None,
        }
    else:
        client_employee = (
            Client_employees.objects.select_related().filter(fk_id_user=user_id).first()
        )
        client = DME_clients.objects.get(
            pk_id_dme_client=client_employee.fk_id_dme_client_id
        )
        return {
            "username": request.user.username,
            "clientname": client.company_name,
            "client_id": client.dme_account_num,
        }
