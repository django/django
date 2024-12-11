from decimal import Decimal

def format(
    number,
    decimal_sep,
    decimal_pos=None,
    grouping=0,
    thousand_sep="",
    force_grouping=False,
    use_l10n=None,
):
    if number is None or number == "":
        return mark_safe(number)
    
    if use_l10n is None:
        use_l10n = True
    use_grouping = use_l10n and settings.USE_THOUSAND_SEPARATOR
    use_grouping = use_grouping or force_grouping
    use_grouping = use_grouping and grouping != 0
    
    # Treat very small floats as Decimals
    if isinstance(number, float) and "e" in str(number).lower():
        number = Decimal(str(number))
    
    if isinstance(number, Decimal):
        if decimal_pos is not None:
            # Adjust the cutoff value to match the precision required by decimal_pos
            cutoff = Decimal("1e-" + str(decimal_pos))
            if abs(number) < cutoff:
                # If the number is smaller than the cutoff, return 0 with trailing zeros
                number = Decimal("0")
        
        # Format as normal
        str_number = "{:f}".format(number)
    else:
        str_number = str(number)
    
    # Sign handling
    sign = ""
    if str_number[0] == "-":
        sign = "-"
        str_number = str_number[1:]
    
    # Split integer and decimal parts
    if "." in str_number:
        int_part, dec_part = str_number.split(".")
        if decimal_pos is not None:
            dec_part = dec_part[:decimal_pos]
    else:
        int_part, dec_part = str_number, ""
    
    # Pad decimal part if needed
    if decimal_pos is not None:
        dec_part += "0" * (decimal_pos - len(dec_part))
    
    dec_part = dec_part and decimal_sep + dec_part
    
    # Grouping logic
    if use_grouping:
        intervals = list(grouping) if isinstance(grouping, tuple) else [grouping, 0]
        active_interval = intervals.pop(0)
        int_part_gd = ""
        cnt = 0
        for digit in int_part[::-1]:
            if cnt and cnt == active_interval:
                if intervals:
                    active_interval = intervals.pop(0) or active_interval
                int_part_gd += thousand_sep[::-1]
                cnt = 0
            int_part_gd += digit
            cnt += 1
        int_part = int_part_gd[::-1]
    
    return sign + int_part + dec_part
