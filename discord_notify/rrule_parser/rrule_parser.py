from icalendar import vRecur
from datetime import datetime, date, time

frequencies = {
    "SECONDLY": "sekund",
    "MINUTELY": "minutt",
    "HOURLY": "time",
    "DAILY": "dag",
    "WEEKLY": "uke",
    "MONTHLY": "måned",
    "YEARLY": "år",
}

prefix_1 = ["hvert", "annenhvert"]
prefix_2 = ["hver", "annenhver"]

frequencies_prefix = {
    "SECONDLY": prefix_1,
    "MINUTELY": prefix_1,
    "HOURLY": prefix_2,
    "DAILY": prefix_2,
    "WEEKLY": prefix_2,
    "MONTHLY": prefix_2,
    "YEARLY": prefix_1
}


def freq_string(rrule_dict: dict) -> str:
    if "FREQ" not in rrule_dict:
        return ""
    result: [str] = []
    for freq_index in range(len(rrule_dict["FREQ"])):
        freq: str = rrule_dict["FREQ"][freq_index]
        interval: int = 0 if "INTERVAL" not in rrule_dict or len(rrule_dict["INTERVAL"]) < freq_index + 1 else int(
            rrule_dict["INTERVAL"][freq_index])
        result = result + ["".join([
            frequencies_prefix[freq][1 if interval == 2 else 0],
            " " if interval < 3 else f" {interval}. ",
            frequencies[freq]
        ])]
    return ", ".join(result)


def until_string(rrule_dict: dict) -> str:
    if "UNTIL" not in rrule_dict or len(rrule_dict["UNTIL"]) == 0:
        return ""
    untils = []
    for until in rrule_dict["UNTIL"]:
        if isinstance(until, datetime):
            untils = untils + [until.strftime('%d/%m/%Y %H:%M')]
        elif isinstance(until, date):
            untils = untils + [until.strftime('%d/%m/%Y')]
        elif isinstance(until, time):
            untils = untils + [until.strftime('%H:%M')]
    return f"frem til {', '.join(untils)}"


def count_string(rrule_dict: dict) -> str:
    if "COUNT" not in rrule_dict or len(rrule_dict["COUNT"]) == 0:
        return ""
    return ", ".join(list(map(lambda count: f"{count} ganger", rrule_dict['COUNT'])))


week_days = {
    "SU": "søndag",
    "MO": "mandag",
    "TU": "tirsdag",
    "WE": "onsdag",
    "TH": "torsdag",
    "FR": "fredag",
    "SA": "lørdag",
}


def byweekday_string(rrule_dict: dict) -> str:
    if "BYWEEKDAY" not in rrule_dict or len(rrule_dict["BYWEEKDAY"]) == 0:
        return ""
    result: [str] = [f"{week_days[weekday]}er" for weekday in rrule_dict["BYWEEKDAY"]]
    if len(result) == 0:
        return ""
    if len(result) == 1:
        return result[0]
    return f"{', '.join(result[0:len(result) - 1])} og {result[-1]}"


pos = {
    "-1": "siste ",
    "-2": "nest siste ",
    "0": "",
    "1": "første ",
    "2": "andre ",
    "3": "tredje ",
    "4": "fjerde ",
}


def byday_string(rrule_dict: dict) -> str:
    if "BYDAY" not in rrule_dict or len(rrule_dict["BYDAY"]) == 0:
        return ""

    def parse_byday_str(byday_str: str) -> str:
        if len(byday_str) < 2:
            raise ValueError("BYDAY must be at least length 2")
        if len(byday_str) == 2:
            return week_days[byday_str]
        day_str: str = byday_str[-2:]
        pos_str: str = byday_str[:-2]
        if pos_str in pos.keys():
            return f"{pos[pos_str]}{week_days[day_str]}"
        return f"hver {pos_str}. {'siste ' if int(pos_str) < 0 else ''} {week_days[day_str]}"

    result_array: [str] = [parse_byday_str(bds) for bds in rrule_dict["BYDAY"]]

    return ", ".join(result_array)


def bymonthday_string(rrule_dict: dict) -> str:
    if "BYMONTHDAY" not in rrule_dict.keys() or len(rrule_dict["BYMONTHDAY"]) == 0:
        return ""
    result_array: [str] = [
        f"{day}." for day in rrule_dict["BYMONTHDAY"]
    ]
    if len(result_array) == 0:
        return ""
    if len(result_array) == 1:
        return f"{result_array[0]} dag i måneden"
    else:
        return f"{', '.join(result_array[:-1])} og {result_array[-1]} dag i måneden"


def byyearday_string(rrule_dict: dict) -> str:
    if "BYYEARDAY" not in rrule_dict.keys() or len(rrule_dict["BYYEARDAY"]) == 0:
        return ""
    result_array: [str] = [
        f"{day}." for day in rrule_dict["BYYEARDAY"]
    ]
    if len(result_array) == 0:
        return ""
    if len(result_array) == 1:
        return f"{result_array[0]} dag i året"
    else:
        return f"{', '.join(result_array[:-1])} og {result_array[-1]} dag i året"


def byweekno_string(rrule_dict: dict) -> str:
    if "BYWEEKNO" not in rrule_dict.keys() or len(rrule_dict["BYWEEKNO"]) == 0:
        return ""
    result_array: [str] = [
        f"{day}." for day in rrule_dict["BYWEEKNO"]
    ]
    if len(result_array) == 0:
        return ""
    if len(result_array) == 1:
        return f"{result_array[0]} uke i året"
    else:
        return f"{', '.join(result_array[:-1])} og {result_array[-1]} uke i året"


months = {
    "1": "januar",
    "2": "februar",
    "3": "mars",
    "4": "april",
    "5": "mai",
    "6": "juni",
    "7": "juli",
    "8": "august",
    "9": "september",
    "10": "oktober",
    "11": "november",
    "12": "desember",
}


def bymonth_string(rrule_dict: dict) -> str:
    if "BYMONTH" not in rrule_dict or len(rrule_dict["BYMONTH"]) == 0:
        return ""
    result: [str] = [months[str(month)] for month in rrule_dict["BYMONTH"]]
    if len(result) == 0:
        return ""
    if len(result) == 1:
        return result[0]
    return f"{', '.join(result[0:len(result) - 1])} og {result[-1]}"


process_funcs: dict = {
    "BYDAY": byday_string,
    "FREQ": freq_string,
    "COUNT": count_string,
    "INTERVAL": lambda _: "",
    "BYSECOND": lambda _: "",
    "BYMINUTE": lambda _: "",
    "BYHOUR": lambda _: "",
    "BYWEEKDAY": byweekday_string,
    "BYMONTHDAY": bymonthday_string,
    "BYYEARDAY": byyearday_string,
    "BYWEEKNO": byweekno_string,
    "BYMONTH": bymonth_string,
    "BYSETPOS": lambda _: "",
    "WKST": lambda _: "",
    "UNTIL": until_string,
}


def from_ical(ical_string: str):
    rrule_dict: dict = vRecur.from_ical(ical_string)
    result_array: [str] = [
        process_funcs[prop](rrule_dict) for prop in process_funcs.keys()
    ]
    result_str: str = ", ".join(list(filter(lambda res: res != "", result_array)))
    return result_str if len(result_str) < 2 else f"{result_str[0].upper()}{result_str[1:]}"
