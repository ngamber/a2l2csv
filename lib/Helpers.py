import decimal


"""
Convert the given float to a string,
without resorting to scientific notation
"""
def float_to_str(f):
    # create a new context for this task
    ctx = decimal.Context()
    ctx.prec = 5

    d1 = ctx.create_decimal(repr(f))
    return format(d1, 'f')