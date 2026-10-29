"""A small item-to-item car recommender for the recommender systems lab."""

from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer
from html import escape
from math import log2
from pathlib import Path
from string import Template
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).parent
PORT = 8765

CARS = {
    "rio": {"name": "Kia Rio", "year": 2020, "body": "Седан", "engine": "1.6 л · автомат", "price": 1_550_000},
    "solaris": {"name": "Hyundai Solaris", "year": 2019, "body": "Седан", "engine": "1.6 л · автомат", "price": 1_480_000},
    "polo": {"name": "Volkswagen Polo", "year": 2021, "body": "Лифтбек", "engine": "1.6 л · автомат", "price": 1_790_000},
    "rapid": {"name": "Škoda Rapid", "year": 2021, "body": "Лифтбек", "engine": "1.4 л · автомат", "price": 1_950_000},
    "corolla": {"name": "Toyota Corolla", "year": 2019, "body": "Седан", "engine": "1.6 л · вариатор", "price": 2_250_000},
    "camry": {"name": "Toyota Camry", "year": 2018, "body": "Седан", "engine": "2.5 л · автомат", "price": 2_850_000},
    "mazda6": {"name": "Mazda 6", "year": 2018, "body": "Седан", "engine": "2.0 л · автомат", "price": 2_600_000},
    "tucson": {"name": "Hyundai Tucson", "year": 2020, "body": "Кроссовер", "engine": "2.0 л · автомат", "price": 3_250_000},
    "sportage": {"name": "Kia Sportage", "year": 2019, "body": "Кроссовер", "engine": "2.0 л · автомат", "price": 2_950_000},
    "rav4": {"name": "Toyota RAV4", "year": 2018, "body": "Кроссовер", "engine": "2.0 л · вариатор", "price": 3_450_000},
    "duster": {"name": "Renault Duster", "year": 2021, "body": "Кроссовер", "engine": "1.6 л · механика", "price": 2_350_000},
    "jolion": {"name": "Haval Jolion", "year": 2022, "body": "Кроссовер", "engine": "1.5 л · робот", "price": 2_650_000},
}

SPECS = {
    "rio": {"power": 123, "fuel": "Бензин", "transmission": "Автомат", "drive": "Передний"},
    "solaris": {"power": 123, "fuel": "Бензин", "transmission": "Автомат", "drive": "Передний"},
    "polo": {"power": 110, "fuel": "Бензин", "transmission": "Автомат", "drive": "Передний"},
    "rapid": {"power": 125, "fuel": "Бензин", "transmission": "Автомат", "drive": "Передний"},
    "corolla": {"power": 122, "fuel": "Бензин", "transmission": "Вариатор", "drive": "Передний"},
    "camry": {"power": 181, "fuel": "Бензин", "transmission": "Автомат", "drive": "Передний"},
    "mazda6": {"power": 150, "fuel": "Бензин", "transmission": "Автомат", "drive": "Передний"},
    "tucson": {"power": 150, "fuel": "Бензин", "transmission": "Автомат", "drive": "Полный"},
    "sportage": {"power": 150, "fuel": "Бензин", "transmission": "Автомат", "drive": "Полный"},
    "rav4": {"power": 149, "fuel": "Бензин", "transmission": "Вариатор", "drive": "Полный"},
    "duster": {"power": 114, "fuel": "Дизель", "transmission": "Механика", "drive": "Полный"},
    "jolion": {"power": 143, "fuel": "Бензин", "transmission": "Робот", "drive": "Передний"},
}

# Synthetic positive feedback: each row represents one other buyer's preferences.
HISTORY_SETS = [
    ("Городской седан", ["rio", "solaris", "polo"]),
    ("Городской седан", ["rio", "solaris", "rapid"]),
    ("Городской седан", ["solaris", "polo", "rapid"]),
    ("Компактный лифтбек", ["rapid", "polo", "corolla"]),
    ("Комфортный седан", ["corolla", "camry", "mazda6"]),
    ("Комфортный седан", ["camry", "corolla", "mazda6"]),
    ("Комфортный седан", ["camry", "mazda6", "tucson"]),
    ("Семейный кроссовер", ["tucson", "sportage", "rav4"]),
    ("Семейный кроссовер", ["tucson", "sportage", "jolion"]),
    ("Поездки за город", ["duster", "rav4", "tucson"]),
    ("Поездки за город", ["duster", "jolion", "tucson"]),
    ("Семейный кроссовер", ["sportage", "rav4", "jolion"]),
]
HISTORIES = [
    {"label": f"История {index:02} · {kind}", "likes": likes}
    for index, (kind, likes) in enumerate(HISTORY_SETS * 2, start=1)
]

TEMPLATE = Template((ROOT / "templates" / "index.html").read_text(encoding="utf-8"))


def money(value):
    return f"{value:,}".replace(",", " ") + " ₽"


def select_options(options, selected, placeholder, prefix="", labels=None):
    rows = [f'<option value="">{placeholder}</option>']
    for value in options:
        label = labels[value] if labels else value
        rows.append(f'<option value="{escape(value)}"{" selected" if value == selected else ""}>{prefix}{escape(label)}</option>')
    return "\n".join(rows)


def pmi(left, right, counts, total_users):
    together = sum(1 for history in HISTORIES if left in history["likes"] and right in history["likes"])
    if not together:
        return None, 0
    score = log2((together * total_users) / (counts[left] * counts[right]))
    return score, together


def recommendations(budget, body, brand, min_year, power, fuel, transmission, drive):
    counts = Counter(car_id for history in HISTORIES for car_id in history["likes"])
    matching = []
    for car_id, car in CARS.items():
        specs = SPECS[car_id]
        matches = (
            car["price"] <= budget
            and (not body or car["body"] == body)
            and (not brand or car["name"].split()[0] == brand)
            and (not min_year or car["year"] >= min_year)
            and (not power or power[0] <= specs["power"] <= power[1])
            and (not fuel or specs["fuel"] == fuel)
            and (not transmission or specs["transmission"] == transmission)
            and (not drive or specs["drive"] == drive)
        )
        if matches:
            matching.append(car_id)

    ranked = []
    for car_id in matching:
        links = []
        for other_id in matching:
            if other_id == car_id:
                continue
            score, together = pmi(car_id, other_id, counts, len(HISTORIES))
            if score is not None:
                links.append({"source": other_id, "score": score, "together": together})
        if links:
            links.sort(key=lambda link: link["score"], reverse=True)
            score = sum(link["score"] for link in links) / len(links)
            score_label = "средний PMI"
            score_text = f"{score:+.2f}"
            reason = None
        else:
            score = counts[car_id] / len(HISTORIES)
            score_label = "покупателей"
            score_text = f"{counts[car_id]} / {len(HISTORIES)}"
            reason = f"Получил положительные оценки от {counts[car_id]} из {len(HISTORIES)} покупателей"
        ranked.append({"id": car_id, "car": CARS[car_id], "score": score, "score_label": score_label, "score_text": score_text, "reason": reason, "links": links})
    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def render(query):
    body = query.get("body", [""])[0]
    if body not in ("", "Седан", "Лифтбек", "Кроссовер"):
        body = ""
    try:
        budget = int(query.get("budget", ["3000000"])[0])
    except ValueError:
        budget = 3_000_000
    budget = max(0, min(budget, 20_000_000))
    brand = query.get("brand", [""])[0]
    brands = sorted({car["name"].split()[0] for car in CARS.values()})
    if brand not in brands:
        brand = ""
    try:
        min_year = int(query.get("year", [""])[0])
    except ValueError:
        min_year = 0
    if min_year not in (0, 2018, 2019, 2020, 2021, 2022):
        min_year = 0
    power_ranges = {"": None, "low": (0, 130), "mid": (131, 160), "high": (161, 500)}
    power_key = query.get("power", [""])[0]
    if power_key not in power_ranges:
        power_key = ""
    fuel = query.get("fuel", [""])[0]
    if fuel not in ("", "Бензин", "Дизель"):
        fuel = ""
    transmission = query.get("transmission", [""])[0]
    if transmission not in ("", "Автомат", "Вариатор", "Механика", "Робот"):
        transmission = ""
    drive = query.get("drive", [""])[0]
    if drive not in ("", "Передний", "Полный"):
        drive = ""

    recs = recommendations(budget, body, brand, min_year, power_ranges[power_key], fuel, transmission, drive)
    if recs:
        result_markup = "\n".join(recommendation_row(item, rank) for rank, item in enumerate(recs, start=1))
    else:
        result_markup = '<div class="empty"><strong>Подходящих автомобилей не найдено</strong><p>Измените параметры поиска и попробуйте ещё раз.</p></div>'
    return TEMPLATE.substitute(
        budget=budget,
        brand_options=select_options(brands, brand, "Любая марка"),
        body_options="\n".join(
            f'<option value="{value}"{" selected" if value == body else ""}>{label}</option>'
            for value, label in (("", "Любой кузов"), ("Седан", "Седан"), ("Лифтбек", "Лифтбек"), ("Кроссовер", "Кроссовер"))
        ),
        year_options=select_options(["2018", "2019", "2020", "2021", "2022"], str(min_year) if min_year else "", "Любой год", "От "),
        power_options=select_options(["low", "mid", "high"], power_key, "Любая мощность", labels={"low": "До 130 л.с.", "mid": "131–160 л.с.", "high": "Более 160 л.с."}),
        fuel_options=select_options(["Бензин", "Дизель"], fuel, "Любое топливо"),
        transmission_options=select_options(["Автомат", "Вариатор", "Механика", "Робот"], transmission, "Любая коробка"),
        drive_options=select_options(["Передний", "Полный"], drive, "Любой привод"),
        results=result_markup,
        result_count=len(recs),
        result_word="автомобилей" if len(recs) in (0, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14) else ("автомобиль" if len(recs) % 10 == 1 else "автомобиля"),
    )


def recommendation_row(item, rank):
    car = item["car"]
    if item["links"]:
        top_link = item["links"][0]
        source = CARS[top_link["source"]]["name"]
        reason = f'Похож на {escape(source)} · {top_link["together"]} общих покупателей · PMI {top_link["score"]:+.2f}'
    else:
        reason = item["reason"]
    return f'''<article class="result-row">
      <span class="rank">{rank:02}</span>
      <div class="car-main"><h3>{escape(car["name"])}</h3><p>{car["year"]} · {escape(car["body"])} · {escape(car["engine"])}</p>
        <p class="reason">{reason}</p></div>
      <div class="car-score"><strong>{item["score_text"]}</strong><span>{item["score_label"]}</span></div>
      <div class="price">{money(car["price"])}</div>
    </article>'''


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path)
        if path.path == "/static/style.css":
            data = (ROOT / "static" / "style.css").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/css; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path.path != "/":
            self.send_error(404)
            return
        data = render(parse_qs(path.query)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    print(f"Приложение запущено: http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), AppHandler).serve_forever()
