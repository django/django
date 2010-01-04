# -*- coding: utf-8 -*-

def get_validation_digit(number):
    """ Calculates the validation digit for the given number. """
    sum = 0
    dvs = [4, 3, 6, 7, 8, 9, 2]
    number = str(number)

    for i in range(0, len(number)):
        sum = (int(number[-1 - i]) * dvs[i] + sum) % 10

    return (10-sum) % 10
