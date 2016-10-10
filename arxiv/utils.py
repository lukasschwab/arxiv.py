# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

from time import sleep


def drip(f, l, t=0):
    result = []

    if l:
        for el in l[:-1]:
            result.append(f(el))
            sleep(t)
        result.append(f(l[-1]))

    return result


def has(d, k):
    return k in d and d[k] is not None
