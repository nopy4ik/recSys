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


def pmi(left, right, counts, total_users):
    together = sum(1 for history in HISTORIES if left in history["likes"] and right in history["likes"])
    if not together:
        return None, 0
    score = log2((together * total_users) / (counts[left] * counts[right]))
    return score, together


def recommendations(liked, budget, body):
    counts = Counter(car_id for history in HISTORIES for car_id in history["likes"])
    ranked = []
    for car_id, car in CARS.items():
        if car_id in liked or car["price"] > budget or (body and car["body"] != body):
            continue
        links = []
        for liked_id in liked:
            score, together = pmi(car_id, liked_id, counts, len(HISTORIES))
            if score is not None:
                links.append({"source": liked_id, "score": score, "together": together})
        if links:
            links.sort(key=lambda link: link["score"], reverse=True)
            ranked.append({"id": car_id, "car": car, "score": sum(link["score"] for link in links) / len(links), "links": links})
    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def render(query):
    liked = list(dict.fromkeys(car_id for car_id in query.get("car", []) if car_id in CARS))
    body = query.get("body", [""])[0]
    if body not in ("", "Седан", "Лифтбек", "Кроссовер"):
        body = ""
    try:
        budget = int(query.get("budget", ["3000000"])[0])
    except ValueError:
        budget = 3_000_000
    budget = max(0, min(budget, 20_000_000))

    car_options = "\n".join(
        f'<label class="car-option"><input type="checkbox" name="car" value="{car_id}"{" checked" if car_id in liked else ""}><span>{escape(car["name"])}</span><small>{car["year"]} · {escape(car["body"])}</small></label>'
        for car_id, car in CARS.items()
    )
    recs = recommendations(liked, budget, body)
    if recs:
        result_markup = "\n".join(recommendation_row(item, rank) for rank, item in enumerate(recs, start=1))
    elif not liked:
        result_markup = '<div class="empty"><strong>Отметьте автомобили, которые вам нравятся</strong><p>Мы сравним ваш выбор с готовой матрицей предпочтений покупателей.</p></div>'
    else:
        result_markup = '<div class="empty"><strong>Подходящих рекомендаций нет</strong><p>Увеличьте бюджет или выберите другой тип кузова.</p></div>'
    return TEMPLATE.substitute(
        car_options=car_options,
        budget=budget,
        body_options="\n".join(
            f'<option value="{value}"{" selected" if value == body else ""}>{label}</option>'
            for value, label in (("", "Любой кузов"), ("Седан", "Седан"), ("Лифтбек", "Лифтбек"), ("Кроссовер", "Кроссовер"))
        ),
        results=result_markup,
        result_count=len(recs),
        result_word="автомобилей" if len(recs) in (0, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14) else ("автомобиль" if len(recs) % 10 == 1 else "автомобиля"),
    )


def recommendation_row(item, rank):
    car = item["car"]
    top_link = item["links"][0]
    source = CARS[top_link["source"]]["name"]
    score = f"{item['score']:+.2f}"
    return f'''<article class="result-row">
      <span class="rank">{rank:02}</span>
      <div class="car-main"><h3>{escape(car["name"])}</h3><p>{car["year"]} · {escape(car["body"])} · {escape(car["engine"])}</p>
        <p class="reason">Похож на {escape(source)} <span>· {top_link["together"]} общих покупателей · PMI {top_link["score"]:+.2f}</span></p></div>
      <div class="car-score"><strong>{score}</strong><span>средний PMI</span></div>
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
