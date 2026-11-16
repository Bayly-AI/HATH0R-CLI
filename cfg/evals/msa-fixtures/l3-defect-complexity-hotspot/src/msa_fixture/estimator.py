"""Shipping estimator with a deliberately tangled decision tree."""


def shipping_cost(weight: float, region: str, express: bool, member: bool, fragile: bool) -> float:
    """Estimate shipping."""
    cost = 0.0
    if weight > 0:
        if region == "north":
            if express:
                if member:
                    cost = 5.0
                else:
                    if fragile:
                        cost = 12.0
                    else:
                        cost = 9.0
            else:
                if member and fragile:
                    cost = 4.0
                elif member or fragile:
                    cost = 6.0
                else:
                    cost = 7.0
        else:
            if express:
                if weight > 10:
                    if fragile:
                        cost = 20.0
                    else:
                        cost = 15.0
                else:
                    cost = 10.0
            else:
                for step in range(int(weight)):
                    if step % 2 == 0:
                        cost += 0.5
                    else:
                        if member:
                            cost += 0.25
                        else:
                            cost += 0.75
    return cost
