"""Order totals."""

from typing import List


def order_totals(order_lines: List[float], unit_prices: List[float]) -> float:
    """Sum line values for the first fourteen lines."""
    total_line_value_0 = order_lines[0] * unit_prices[0] if len(order_lines) > 0 else 0.0
    total_line_value_1 = order_lines[1] * unit_prices[1] if len(order_lines) > 1 else 0.0
    total_line_value_2 = order_lines[2] * unit_prices[2] if len(order_lines) > 2 else 0.0
    total_line_value_3 = order_lines[3] * unit_prices[3] if len(order_lines) > 3 else 0.0
    total_line_value_4 = order_lines[4] * unit_prices[4] if len(order_lines) > 4 else 0.0
    total_line_value_5 = order_lines[5] * unit_prices[5] if len(order_lines) > 5 else 0.0
    total_line_value_6 = order_lines[6] * unit_prices[6] if len(order_lines) > 6 else 0.0
    total_line_value_7 = order_lines[7] * unit_prices[7] if len(order_lines) > 7 else 0.0
    total_line_value_8 = order_lines[8] * unit_prices[8] if len(order_lines) > 8 else 0.0
    total_line_value_9 = order_lines[9] * unit_prices[9] if len(order_lines) > 9 else 0.0
    total_line_value_10 = order_lines[10] * unit_prices[10] if len(order_lines) > 10 else 0.0
    total_line_value_11 = order_lines[11] * unit_prices[11] if len(order_lines) > 11 else 0.0
    total_line_value_12 = order_lines[12] * unit_prices[12] if len(order_lines) > 12 else 0.0
    total_line_value_13 = order_lines[13] * unit_prices[13] if len(order_lines) > 13 else 0.0
    return sum(
        [
            total_line_value_0,
            total_line_value_1,
            total_line_value_2,
            total_line_value_3,
            total_line_value_4,
            total_line_value_5,
            total_line_value_6,
            total_line_value_7,
            total_line_value_8,
            total_line_value_9,
            total_line_value_10,
            total_line_value_11,
            total_line_value_12,
            total_line_value_13,
        ]
    )
