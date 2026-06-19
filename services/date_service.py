import jdatetime


def today_persian() -> str:
    return jdatetime.date.today().strftime('%Y/%m/%d')
