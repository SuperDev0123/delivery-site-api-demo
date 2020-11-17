import requests
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from api.models import Tokens


@api_view(["GET"])
@permission_classes((AllowAny,))
def get_auth_zoho_tickets(request):
    if Tokens.objects.filter(type="access_token").count() == 0:
        response = redirect(
            "https://accounts.zoho.com.au/oauth/v2/auth?response_type=code&client_id="
            + settings.CLIENT_ID_ZOHO
            + "&scope=Desk.tickets.ALL&redirect_uri="
            + settings.REDIRECT_URI_ZOHO
            + "&state=-5466400890088961855"
            + "&prompt=consent&access_type=offline&dmeid="
        )

        return response
    else:
        get_all_zoho_tickets(1)


@api_view(["GET"])
@permission_classes((AllowAny,))
def get_all_zoho_tickets(request):
    dmeid = 0

    if Tokens.objects.filter(type="access_token").count() == 0:
        dat = request.GET.get("code")
        if not dat:
            dat = ""

        response = requests.post(
            "https://accounts.zoho.com.au/oauth/v2/token?code="
            + dat
            + "&grant_type=authorization_code&client_id="
            + settings.CLIENT_ID_ZOHO
            + "&client_secret="
            + settings.CLIENT_SECRET_ZOHO
            + "&redirect_uri="
            + settings.REDIRECT_URI_ZOHO
            + "&prompt=consent&access_type=offline"
        ).json()

        refresh_token = response["refresh_token"]
        access_token = response["access_token"]

        Tokens.objects.all().delete()
        Tokens(
            value=access_token,
            type="access_token",
            z_createdTimeStamp=datetime.utcnow(),
            z_expiryTimeStamp=datetime.utcnow() + timedelta(hours=1),
        ).save()
        Tokens(
            value=refresh_token,
            type="refresh_token",
            z_createdTimeStamp=datetime.utcnow(),
            z_expiryTimeStamp=datetime.utcnow() + timedelta(hours=1),
        ).save()
        headers_for_tickets = {
            "content-type": "application/json",
            "orgId": settings.ORG_ID,
            "Authorization": "Zoho-oauthtoken " + response["access_token"],
        }
        get_tickets = requests.get(
            "https://desk.zoho.com.au/api/v1/tickets",
            data={},
            headers=headers_for_tickets,
        )

    else:
        dmeid = request.GET.get("dmeid")
        data = Tokens.objects.filter(type="access_token")
        tz_info = data[0].z_expiryTimeStamp.tzinfo
        present_time = datetime.now(tz_info)

        if data[0].z_expiryTimeStamp > present_time:
            headers_for_tickets = {
                "content-type": "application/json",
                "orgId": settings.ORG_ID,
                "Authorization": "Zoho-oauthtoken " + data[0].value,
            }
            get_tickets = requests.get(
                "https://desk.zoho.com.au/api/v1/tickets",
                data={},
                headers=headers_for_tickets,
            )
        else:
            data = Tokens.objects.filter(type="refresh_token")
            response = requests.post(
                "https://accounts.zoho.com.au/oauth/v2/token?refresh_token="
                + data[0].value
                + "&grant_type=refresh_token&client_id="
                + settings.CLIENT_ID_ZOHO
                + "&client_secret="
                + settings.CLIENT_SECRET_ZOHO
                + "&redirect_uri="
                + settings.REDIRECT_URI_ZOHO
                + "&prompt=consent&access_type=offline"
            ).json()
            updatedata = Tokens.objects.get(type="access_token")
            updatedata.value = response["access_token"]
            updatedata.z_createdTimeStamp = datetime.utcnow()
            updatedata.z_expiryTimeStamp = datetime.utcnow() + timedelta(hours=1)
            updatedata.save()
            headers_for_tickets = {
                "content-type": "application/json",
                "orgId": settings.ORG_ID,
                "Authorization": "Zoho-oauthtoken " + response["access_token"],
            }
            get_tickets = requests.get(
                "https://desk.zoho.com.au/api/v1/tickets",
                data={},
                headers=headers_for_tickets,
            )
    get_ticket = []

    if get_tickets.status_code == 200:
        data = Tokens.objects.filter(type="access_token")
        for ticket in get_tickets.json()["data"]:
            headers_for_single_ticket = {
                "content-type": "application/json",
                "orgId": settings.ORG_ID,
                "Authorization": "Zoho-oauthtoken " + data[0].value,
            }
            ticket_data = requests.get(
                "https://desk.zoho.com.au/api/v1/tickets/" + ticket["id"],
                data={},
                headers=headers_for_single_ticket,
            ).json()

            if ticket_data["customFields"]["DME Id/Consignment No."] == dmeid:
                get_ticket.append(ticket_data)
        if not get_ticket:
            return JsonResponse(
                {
                    "status": "No ticket with this DME Id is available.",
                    "tickets": get_ticket,
                }
            )
        else:
            final_ticket = {"status": "success", "tickets": get_ticket}
            return JsonResponse(final_ticket)
    elif get_tickets.status_code == 204:
        return JsonResponse(
            {
                "status": "There are no tickets on zoho",
                "tickets": get_ticket,
            }
        )
    else:
        final_ticket = {"status": "success", "tickets": get_ticket}
        return JsonResponse(final_ticket)
