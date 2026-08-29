def hex_distance(a, b):
    dq = a.q - b.q
    dr = a.r - b.r
    ds = (a.q + a.r) - (b.q + b.r)
    return max(abs(dq), abs(dr), abs(ds))
