import requests, json
from datetime import datetime, date, timedelta

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from api.models import Tokens, Bookings, ZohoTicketSummary


@api_view(["GET"])
@permission_classes((AllowAny,))
def get_auth_zoho_tickets(request):
    if Tokens.objects.filter(type="access_token").count() == 0:
        response = redirect(
            "https://accounts.zoho.com.au/oauth/v2/auth?response_type=code&client_id="
            + settings.CLIENT_ID_ZOHO
            + "&scope=Desk.tickets.ALL,Desk.basic.ALL&redirect_uri="
            + settings.REDIRECT_URI_ZOHO
            + "&state=-5466400890088961855"
            + "&prompt=consent&access_type=offline"
        )

        return response
    else:
        return redirect(settings.WEB_SITE_URL + "/api/get_all_zoho_tickets/")


def get_zoho_access_token(request):
    access_token = None
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

    else:
        data = Tokens.objects.filter(type="access_token")
        tz_info = data[0].z_expiryTimeStamp.tzinfo
        present_time = datetime.now(tz_info)

        if data[0].z_expiryTimeStamp <= present_time:
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
            access_token = response["access_token"]
        else:
            access_token = data[0].value
    return access_token


@api_view(["GET"])
@permission_classes((AllowAny,))
def get_all_zoho_tickets(request):
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    all_tickets = requests.get(
        "https://desk.zoho.com.au/api/v1/tickets?limit=50",
        data={},
        headers=headers_for_tickets,
    )

    if all_tickets.status_code == 200:
        final_ticket = {"status": "success", "tickets": all_tickets.json()["data"]}
        return JsonResponse(final_ticket)
    elif all_tickets.status_code == 204:
        return JsonResponse(
            {
                "status": "There are no tickets on zoho",
                "tickets": [],
            }
        )
    else:
        final_ticket = {"status": all_tickets.status_code, "tickets": []}
        return JsonResponse(final_ticket)


@api_view(["GET"])
@permission_classes((AllowAny,))
def get_zoho_tickets_with_booking_id(request):
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    ticket_list = requests.get(
        "https://desk.zoho.com.au/api/v1/tickets?limit=100",
        headers=headers_for_tickets,
    )

    dmeid = request.GET.get("dmeid") or ""
    booking = Bookings.objects.filter(b_bookingID_Visual=dmeid)
    if booking:
        # order_num = booking[0].b_client_order_num
        invoice_num = booking[0].b_client_sales_inv_num
    else:
        # order_num, invoice_num = None, None
        invoice_num = ""
    tickets = []
    if ticket_list.status_code == 200:
        data = Tokens.objects.filter(type="access_token")
        for ticket in ticket_list.json()["data"]:
            headers = {
                "content-type": "application/json",
                "orgId": settings.ORG_ID,
                "Authorization": "Zoho-oauthtoken " + data[0].value,
            }

            ticket_response = requests.get(
                "https://desk.zoho.com.au/api/v1/tickets/" + ticket["id"],
                headers=headers,
            )

            if ticket_response.status_code == 200:
                ticket_data = ticket_response.json()
                to_be_checked = f"{ticket_data['subject'] or ''} {ticket_data['cf']['cf_dme_id_consignment_no'] or ''}"
                # if (dmeid and dmeid in to_be_checked) or (order_num and order_num in to_be_checked) or (invoice_num and invoice_num in to_be_checked):
                if (dmeid and dmeid in to_be_checked) or (
                    invoice_num and invoice_num in to_be_checked
                ):
                    tickets.append(ticket_data)
                # else:
                #     ticket_details = requests.get(
                #         "https://desk.zoho.com.au/api/v1/tickets/"
                #         + ticket["id"]
                #         + "/conversations",
                #         headers=headers,
                #     )
                #     if ticket_details.status_code == 200:
                #         for item in ticket_details.json()["data"]:
                #             content = None
                #             if item["type"] == "thread":
                #                 thread = requests.get(
                #                     "https://desk.zoho.com.au/api/v1/tickets/"
                #                     + ticket["id"]
                #                     + "/threads/"
                #                     + item["id"]
                #                     + "?include=plainText",
                #                     headers=headers,
                #                 )
                #                 if thread.status_code == 200:
                #                     content = thread.json()["plainText"]
                #             else:
                #                 comment = requests.get(
                #                     "https://desk.zoho.com.au/api/v1/tickets/"
                #                     + ticket["id"]
                #                     + "/comments/"
                #                     + item["id"],
                #                     headers=headers,
                #                 )
                #                 if comment.status_code == 200:
                #                     content = comment.json()["content"]

                #             if (dmeid and content and dmeid in content) or (
                #                 invoice_num and content and invoice_num in content
                #             ):
                #                 tickets.append(ticket_data)
                #                 continue
        if not tickets:
            return JsonResponse(
                {
                    "status": "No ticket with this DME Id is available.",
                    "tickets": tickets,
                }
            )
        else:
            final_ticket = {"status": "success", "tickets": tickets}
            return JsonResponse(final_ticket)
    elif ticket_list.status_code == 204:
        return JsonResponse(
            {
                "status": "There are no tickets on zoho",
                "tickets": tickets,
            }
        )
    else:
        final_ticket = {"status": "failed", "tickets": []}
        return JsonResponse(final_ticket)


@api_view(["POST"])
@permission_classes((AllowAny,))
def merge_zoho_tickets(request):
    data = request.data
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    merged_result = requests.post(
        "https://desk.zoho.com.au/api/v1/tickets/" + data["id"] + "/merge",
        data=json.dumps({"ids": data["ids"], "source": data["source"]}),
        headers=headers_for_tickets,
    )

    res = {"status": merged_result.status_code, "result": merged_result.json()}
    return JsonResponse(res)


@api_view(["POST"])
@permission_classes((AllowAny,))
def close_zoho_ticket(request):
    data = request.data
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    closed_result = requests.patch(
        "https://desk.zoho.com.au/api/v1/tickets/" + data["id"],
        data=json.dumps({"status": "Closed"}),
        headers=headers_for_tickets,
    )

    res = {"status": closed_result.status_code, "result": closed_result.json()}
    return JsonResponse(res)


@api_view(["POST"])
@permission_classes((AllowAny,))
def update_zoho_ticket(request):
    data = request.data
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    updated_ticket = requests.patch(
        "https://desk.zoho.com.au/api/v1/tickets/" + data["id"],
        data=json.dumps(data["data"]),
        headers=headers_for_tickets,
    )

    return JsonResponse(
        {"status": updated_ticket.status_code, "result": updated_ticket.json()}
    )


@api_view(["POST"])
@permission_classes((AllowAny,))
def move_zoho_ticket(request):
    data = request.data
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    updated_ticket = requests.post(
        "https://desk.zoho.com.au/api/v1/tickets/" + data["id"] + "/move",
        data=json.dumps(data["data"]),
        headers=headers_for_tickets,
    )

    return JsonResponse({"status": updated_ticket.status_code})


@api_view(["POST"])
@permission_classes((AllowAny,))
def get_zoho_ticket_details(request):
    data = request.data
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    ticket_details = requests.get(
        "https://desk.zoho.com.au/api/v1/tickets/" + data["id"],
        headers=headers_for_tickets,
    )

    res = ticket_details.json()
    return JsonResponse(res)


@api_view(["POST"])
@permission_classes((AllowAny,))
def get_zoho_ticket_conversation_list(request):
    data = request.data
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    ticket_conversations = requests.get(
        "https://desk.zoho.com.au/api/v1/tickets/" + data["id"] + "/conversations",
        headers=headers_for_tickets,
    )
    res = ticket_conversations.json()
    return JsonResponse(res)


@api_view(["POST"])
@permission_classes((AllowAny,))
def get_zoho_ticket_thread(request):
    data = request.data
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    ticket_threads = requests.get(
        "https://desk.zoho.com.au/api/v1/tickets/"
        + data["id"]
        + "/threads/"
        + data["item"]
        + "?include=plainText",
        headers=headers_for_tickets,
    )

    res = ticket_threads.json()
    return JsonResponse(res)


@api_view(["POST"])
@permission_classes((AllowAny,))
def get_zoho_ticket_comment(request):
    data = request.data
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    ticket_comments = requests.get(
        "https://desk.zoho.com.au/api/v1/tickets/"
        + data["id"]
        + "/comments/"
        + data["item"],
        headers=headers_for_tickets,
    )

    res = ticket_comments.json()
    return JsonResponse(res)


@api_view(["POST"])
@permission_classes((AllowAny,))
def send_zoho_ticket_reply(request):
    data = request.data
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    replied_result = requests.post(
        "https://desk.zoho.com.au/api/v1/tickets/" + data["id"] + "/sendReply",
        data=json.dumps(
            {
                "channel": "EMAIL",
                "to": data["to"],
                "fromEmailAddress": data["from"],
                "contentType": "html",
                # 'subject' : '#' +threadcontent.ticketNumber + ' ' + threadcontent.subject,
                "content": data["content"],
                "isForward": True,
            }
        ),
        headers=headers_for_tickets,
    )

    res = replied_result.json()
    return JsonResponse(res)


@api_view(["GET"])
@permission_classes((AllowAny,))
def get_zoho_departments(request):
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    get_result = requests.get(
        "https://desk.zoho.com.au/api/v1/departments?isEnabled=true&chatStatus=AVAILABLE",
        headers=headers_for_tickets,
    )
    if get_result.status_code == 200:
        res = get_result.json()["data"]
    else:
        res = []
    return JsonResponse({"status": get_result.status_code, "data": res})


@api_view(["GET"])
@permission_classes((AllowAny,))
def get_zoho_ticket_summaries(request):
    access_token = get_zoho_access_token(request)
    headers_for_tickets = {
        "content-type": "application/json",
        "orgId": settings.ORG_ID,
        "Authorization": "Zoho-oauthtoken " + access_token,
    }
    summaries = ZohoTicketSummary.objects.values_list("summary", flat=True).order_by(
        "summary"
    )
    return JsonResponse(list(summaries), safe=False)
