from decimal import Decimal, getcontext


def approximate_pi(num_terms: int = 1_000_000) -> Decimal:
    getcontext().prec = 30
    total = Decimal(0)
    sign = 1

    for i in range(num_terms):
        term = Decimal(1) / Decimal(2 * i + 1)
        total += sign * term
        sign *= -1

    return total * 4


if __name__ == "__main__":
    pi_approx = approximate_pi()
    print(pi_approx)
