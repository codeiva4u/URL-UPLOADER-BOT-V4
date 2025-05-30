import math
import time
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from plugins.script import Translation
from pyrogram import enums 
import re




async def progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if current == total or diff > 1:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "{0}{1}".format(
            ''.join(["████" for i in range(math.floor(percentage * 0.1))]),
            ''.join(["░░░░" for i in range(12 - math.floor(percentage * 0.1))])
        )

        tmp = progress + "\nP: {0}%\n".format(round(percentage, 2)) + Translation.PROGRESS.format(
            round(percentage, 2),
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(
              text= Translation.PROGRES.format(
              ud_type,
              tmp
                ),
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [ 
                        InlineKeyboardButton('⛔ Cancel', callback_data=f"cancel_download+{id}")
                       ]
                   ]
                 )
            )
        except:
            pass


def string_to_bytes(size_str: str) -> int:
    size_str = size_str.strip().upper()
    if not size_str or size_str == "UNKNOWNB":
        return 0

    multipliers = {
        'B': 1,
        'K': 2**10, 'KB': 2**10, 'KIB': 2**10,
        'M': 2**20, 'MB': 2**20, 'MIB': 2**20,
        'G': 2**30, 'GB': 2**30, 'GIB': 2**30,
        'T': 2**40, 'TB': 2**40, 'TIB': 2**40,
    }
    
    match = re.match(r"^([\d\.]+)\s*([KMGT]?I?B|[KMGTB])?$", size_str)
    if not match:
        if re.match(r"^[\d\.]+$", size_str):
            return int(float(size_str))
        return 0

    value_str, unit = match.groups()
    value = float(value_str)

    if unit is None:
        unit = 'B'
    
    multiplier = 1
    for key_suffix in [unit, unit + 'B' if not unit.endswith('B') else None]:
        if key_suffix is None:
            continue
        normalized_unit = key_suffix
        if "IB" not in normalized_unit and len(normalized_unit) > 1 and normalized_unit.endswith("B"):
             if normalized_unit[:-1] in multipliers:
                 multiplier = multipliers.get(normalized_unit[:-1], 1)
                 break
        if normalized_unit in multipliers:
            multiplier = multipliers.get(normalized_unit, 1)
            break
            
    return int(value * multiplier)

def humanbytes(size):
    # https://stackoverflow.com/a/49361727/4723940
    # 2**10 = 1024
    if not size:
        return ""
    power = 2 ** 10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
          ((str(hours) + "h, ") if hours else "") + \
          ((str(minutes) + "m, ") if minutes else "") + \
          ((str(seconds) + "s, ") if seconds else "") + \
          ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]
