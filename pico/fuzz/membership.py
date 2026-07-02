# membership.py
# Provides standard membership function generators for fuzzy sets.

def triangular(a, b, c):
    """
    Triangular membership function.
    a: left foot, b: peak, c: right foot
    """
    def fn(x):
        try:
            if x <= a or x >= c:
                return 0.0
            elif x == b:
                return 1.0
            elif a < x < b:
                return (x - a) / (b - a)
            elif b < x < c:
                return (c - x) / (c - b)
            return 0.0  # fallback in weird cases.
        except Exception as e:
            print("Triangular membership error:", e)
            return 0.0
    return fn

def trapezoidal(a, b, c, d):
    """
    Trapezoidal membership function.
    a: left foot, b: left shoulder, c: right shoulder, d: right foot
    """
    def fn(x):
        try:
            if x <= a or x >= d:
                return 0.0
            elif b <= x <= c:
                return 1.0
            elif a < x < b:
                return (x - a) / (b - a)
            elif c < x < d:
                return (d - x) / (d - c)
            return 0.0  # fallback in weird cases.
        except Exception as e:
            print("Trapezoidal membership error:", e)
            return 0.0
    return fn

def gaussian(c, sigma):
    """
    Gaussian membership function.
    c = center (mean)
    sigma = standard deviation (controls width)
    """
    from math import exp
    def fn(x):
        try:
            return exp(-0.5 * ((x - c) / sigma) ** 2)
        except Exception as e:
            print("Gaussian membership error:", e)
            return 0.0
    return fn
