def is_mobile(mobile):
    temp = mobile.replace(" ", "")
    if (
        (len(temp) == 10 and temp[:2] == '04')
        or (len(temp) == 9 and temp[:1] == '4')
        or (len(temp) == 11 and temp[:3] == '614')
        or (len(temp) == 12 and temp[:4] == '+614')
    ):
        return True
    else:
        return False


def format_mobile(mobile):
    temp = mobile.replace(" ", "")
    if len(temp) == 9 and temp[:1] == '4':
        return f"+61{temp}"
    elif len(temp) == 10 and temp[:2] == '04':
        return f"+61{temp[1:]}"
    elif len(temp) == 11 and temp[:3] == '614':
        return f"+{temp}"
    elif len(temp) == 12 and temp[:4] == '+614':
        return temp
