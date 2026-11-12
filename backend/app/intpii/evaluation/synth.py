"""Synthetic English PII documents with exact gold spans. Fake data only."""
from __future__ import annotations

import random
from dataclasses import dataclass

FIRST = ["Alice", "Bob", "Chen", "Dana", "Elena", "Farid", "Grace", "Hugo", "Ingrid", "Jamal",
         "Katya", "Liam", "Maya", "Noah", "Olivia", "Priya", "Quinn", "Rosa", "Sven", "Tara",
         "Will", "Rose", "Mark", "April", "Grant", "Hope"]
LAST = ["Smith", "Nguyen", "Okafor", "Larsen", "Garcia", "Patel", "Kowalski", "Brown", "Rossi",
        "Haddad", "Baker", "Young", "Page", "Fox", "Bell", "Stone", "Singh", "Muller"]
STREET = ["Elm Road", "Baker Street", "Mill Lane", "Oak Avenue", "High Street", "Maple Drive",
          "Church Way", "Station Road", "Park Lane", "Harbour View"]
CITY = ["Leeds", "Springfield", "Austin", "Bristol", "Portland", "Dundee", "Boulder", "Cardiff"]
UK_PC = ["LS1 4AP", "NW1 6XE", "BS8 1TH", "CF10 3AT", "DD1 4HN"]
US_ST = ["IL", "TX", "OR", "CO"]
DOMAIN = ["example.com", "mail.example.org", "corp.example.net"]

# Hard negatives: numbers and capitalised words that are NOT PII.
NEGATIVES = [
    "The order contains 42 items and version 3.1 shipped in 2023.",
    "Room 12 will open at 9 and close at 17 on floor 3.",
    "Total: 1250 units, ref 20240117, batch 55 of 60.",
    "We will rose-tint the plan; the grant will cover April costs.",
    "Ticket #48213 was closed after 15 minutes.",
]


@dataclass
class Doc:
    text: str
    gold: list[tuple[str, int, int]]  # (label, start, end)


def _person(r: random.Random) -> str:
    return f"{r.choice(FIRST)} {r.choice(LAST)}"


def _age_phrase(r: random.Random, n: int) -> list:
    return r.choice([
        ["aged ", ("AGE", str(n))],
        [("AGE", str(n)), " years old"],
        ["age: ", ("AGE", str(n))],
        [("AGE", str(n)), "-year-old"],
    ])


def _address(r: random.Random) -> str:
    num = r.randint(1, 240)
    street = r.choice(STREET)
    kind = r.randrange(4)
    if kind == 0:
        return f"{num}{r.choice(['', 'A', 'B'])} {street}, {r.choice(CITY)} {r.choice(UK_PC)}"
    if kind == 1:
        return f"{num} {street}, {r.choice(CITY)}, {r.choice(US_ST)} {r.randint(10000, 99999)}"
    if kind == 2:
        return f"Flat {r.randint(1, 20)}, {r.choice(LAST)} House, {street}, {r.choice(CITY)}"
    return f"{num} {street}, {r.choice(CITY)}"


def _phone(r: random.Random) -> str:
    kind = r.randrange(4)
    a, b, c = r.randint(200, 989), r.randint(100, 999), r.randint(1000, 9999)
    if kind == 0:
        return f"+1 ({a}) {b}-{c}"
    if kind == 1:
        return f"{a}-{b}-{c}"
    if kind == 2:
        return f"+44 {r.randint(20, 79)} {r.randint(1000, 9999)} {r.randint(1000, 9999)}"
    return f"020 {r.randint(1000, 9999)} {r.randint(1000, 9999)}"


def _email(r: random.Random, name: str) -> str:
    f, l = name.lower().split()
    return f"{f}{r.choice(['.', '_', ''])}{l}@{r.choice(DOMAIN)}"


def _template(r: random.Random) -> list:
    name = _person(r)
    age = r.randint(5, 99)
    email = _email(r, name)
    k = r.randrange(5)
    if k == 0:
        return ["Dear ", ("PERSON", name), ", we received your form. You can reach us or reply to ",
                ("EMAIL", email), ". Our records show you live at ", ("ADDRESS", _address(r)), "."]
    if k == 1:
        return ["Patient ", ("PERSON", name), " (", *_age_phrase(r, age), ") called from ",
                ("PHONE", _phone(r)), " to confirm the visit."]
    if k == 2:
        return ["hey its ", ("PERSON", name), " pls send the parcel to ", ("ADDRESS", _address(r)),
                " thx, my number is ", ("PHONE", _phone(r))]
    if k == 3:
        return ["Applicant: ", ("PERSON", name), "\nAge: ", ("AGE", str(age)), "\nEmail: ",
                ("EMAIL", email), "\nAddress: ", ("ADDRESS", _address(r)), "\nPhone: ",
                ("PHONE", _phone(r))]
    return ["Meeting notes: ", ("PERSON", name), " and ", ("PERSON", _person(r)),
            " agreed to follow up. Contact ", ("PERSON", _person(r)), " on ", ("PHONE", _phone(r)), "."]


def make_doc(r: random.Random, negative_rate: float = 0.3) -> Doc:
    parts = _template(r)
    if r.random() < negative_rate:
        parts = [*parts, " ", r.choice(NEGATIVES)]
    text, gold = "", []
    for p in parts:
        if isinstance(p, tuple):
            label, value = p
            gold.append((label, len(text), len(text) + len(value)))
            text += value
        else:
            text += p
    return Doc(text, gold)


def generate(n: int, seed: int = 0) -> list[Doc]:
    r = random.Random(seed)
    return [make_doc(r) for _ in range(n)]
