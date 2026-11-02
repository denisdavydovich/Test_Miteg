"""Независимая проверка daily_by_sku.csv: пересчёт через SQL (sqlite3) и контрольные суммы.

Запуск: python check.py [sales.csv] [daily_by_sku.csv]
"""
import csv
import sqlite3
import sys

src = sys.argv[1] if len(sys.argv) > 1 else "sales.csv"
res = sys.argv[2] if len(sys.argv) > 2 else "daily_by_sku.csv"

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE raw (order_id TEXT, order_date TEXT, sku TEXT, quantity TEXT, price TEXT, status TEXT)")
with open(src, encoding="utf-8", newline="") as f:
    db.executemany("INSERT INTO raw VALUES (?,?,?,?,?,?)", list(csv.reader(f))[1:])

# Дубли убираем через DISTINCT по полной строке (в коде - по order_id), статус нормализуем через SQL
expected = db.execute("""
    WITH clean AS (
        SELECT DISTINCT order_id, order_date, sku,
               CAST(NULLIF(TRIM(quantity), '') AS INTEGER) AS qty,
               CAST(price AS INTEGER) AS price,
               CASE WHEN LOWER(TRIM(status)) = 'delivered' THEN 'delivered' ELSE 'cancelled' END AS status
        FROM raw)
    SELECT sku, order_date, COUNT(DISTINCT order_id),
           COALESCE(SUM(CASE WHEN status = 'delivered' THEN qty * price END), 0)
    FROM clean GROUP BY sku, order_date ORDER BY sku, order_date
""").fetchall()

with open(res, encoding="utf-8", newline="") as f:
    rows = list(csv.reader(f))
assert rows[0] == ["sku", "order_date", "orders", "revenue"], "неверные заголовки"
actual = [(r[0], r[1], int(r[2]), int(r[3])) for r in rows[1:]]

assert actual == expected, "результат не совпал с SQL-пересчётом"
print(f"OK: {len(actual)} строк совпали с SQL-пересчётом (значения и порядок)")

# Контрольные суммы
unique_ids = db.execute("SELECT COUNT(DISTINCT order_id) FROM raw").fetchone()[0]
print(f"Уникальных order_id в выгрузке: {unique_ids}; сумма orders в результате: {sum(r[2] for r in actual)}")
assert unique_ids == sum(r[2] for r in actual)

delivered_total = db.execute("""
    SELECT SUM(q * p) FROM (SELECT DISTINCT order_id, CAST(quantity AS INTEGER) q, CAST(price AS INTEGER) p
                            FROM raw WHERE LOWER(TRIM(status)) = 'delivered')
""").fetchone()[0]
print(f"Выручка по выгрузке: {delivered_total}; сумма revenue в результате: {sum(r[3] for r in actual)}")
assert delivered_total == sum(r[3] for r in actual)

assert len({(r[0], r[1]) for r in actual}) == len(actual), "есть повторы пар sku+date"
print("OK: контрольные суммы сошлись, пар sku+date без повторов")
