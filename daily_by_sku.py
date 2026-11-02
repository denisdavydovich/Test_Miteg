"""Считает заказы и выручку по связке «артикул - день» из выгрузки sales.csv.

Запуск: python daily_by_sku.py [входной_файл] [выходной_файл]
По умолчанию: sales.csv -> daily_by_sku.csv
"""
import csv
import sys
from collections import defaultdict

STATUS_ALIASES = {
    "delivered": "delivered",
    "cancelled": "cancelled",
    "canceled": "cancelled",  # американское написание
}


def normalize_status(raw):
    """Убирает пробелы и регистр, сводит написания к delivered / cancelled."""
    status = STATUS_ALIASES.get(raw.strip().lower())
    if status is None:
        raise ValueError(f"неизвестный статус: {raw!r}")
    return status


def read_orders(path):
    """Читает выгрузку и возвращает словарь {order_id: заказ} без дублей."""
    orders = {}
    duplicates = 0
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            order_id = row["order_id"].strip()
            quantity = row["quantity"].strip()
            order = {
                "order_date": row["order_date"].strip(),
                "sku": row["sku"].strip(),
                # пропуск количества оставляем как None: для отменённых он не важен
                "quantity": int(quantity) if quantity else None,
                "price": int(row["price"]),
                "status": normalize_status(row["status"]),
            }
            if order_id in orders:
                duplicates += 1
                if orders[order_id] != order:
                    print(f"ВНИМАНИЕ: заказ {order_id} повторяется с разными данными, "
                          "оставлена первая строка", file=sys.stderr)
                continue
            orders[order_id] = order
    print(f"Прочитано уникальных заказов: {len(orders)}, отброшено дублей: {duplicates}")
    return orders


def aggregate(orders):
    """Считает orders и revenue по (sku, order_date)."""
    stats = defaultdict(lambda: {"orders": 0, "revenue": 0})
    for order_id, o in orders.items():
        cell = stats[(o["sku"], o["order_date"])]
        cell["orders"] += 1  # отменённые тоже считаются
        if o["status"] == "delivered":
            if o["quantity"] is None:
                raise ValueError(f"у выкупленного заказа {order_id} нет количества")
            cell["revenue"] += o["quantity"] * o["price"]
    return stats


def write_result(stats, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "order_date", "orders", "revenue"])
        for (sku, order_date), cell in sorted(stats.items()):
            writer.writerow([sku, order_date, cell["orders"], cell["revenue"]])


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "sales.csv"
    dst = sys.argv[2] if len(sys.argv) > 2 else "daily_by_sku.csv"
    stats = aggregate(read_orders(src))
    write_result(stats, dst)
    print(f"Строк в результате: {len(stats)}. Файл: {dst}")


if __name__ == "__main__":
    main()
