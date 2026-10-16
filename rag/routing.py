"""Route a visitor's question to the right Engineering Advancement staff member (Story 9).

Retrieval alone finds the right person when the question uses the directory's own wording, but
misses questions like "I live in Atlanta, who can I meet with?". This module matches the question
against a table of topics (departments, programs, regions) and returns the staff who own them.

Names, emails and phone numbers are never written here. Each route names a phrase to look for in
the scraped staff directory, and the contact details come from whoever's entry contains it, so
re-scraping the directory updates the routes. `python routing.py` prints the table and flags
routes whose phrase no longer matches anyone.
"""

import re

from content import DEPARTMENT_KEYWORDS, STAFF_DIRECTORY_URL, _contact, _liaisons, _staff_records

# Only route when the visitor is asking for a person, not for general information.
CONTACT_INTENT = re.compile(
    r"\b(who|whom|contact|talk|speak|reach|meet|call|email|liaison|officer|someone|somebody|"
    r"person|in charge|handles?|runs?|manages?|responsible|get in touch|connect)\b", re.I)

# Extra ways visitors refer to a department, beyond the DEPARTMENT_KEYWORDS themselves.
DEPARTMENT_ALIASES = {
    "computer science": r"computer science|software engineering|\bcsse\b",
    "electrical": r"electrical|computer engineering|\bece\b",
    "industrial": r"industrial|\bise\b",
}

# (topic as it reads in "the contact for <topic>", pattern in the visitor's question,
#  phrase that identifies the owner in the staff directory)
PROGRAM_ROUTES = [
    ("100+ Women Strong", r"100\s*\+?\s*women|women strong", "Program Director for 100+ Women Strong"),
    ("the Brick program", r"\bbricks?\b", "Brick program"),
    ("room naming opportunities",
     r"\bnam(?:e|ing)\b.*\b(?:room|lab|building|space)|\b(?:room|lab|building|space)\b.*\bnam(?:e|ing)\b"
     r"|naming (?:opportunit|rights)", "naming opportunities"),
    ("the Engineering Eagles Society", r"\beagles? society", "Eagles Society"),
    ("donor events and stewardship",
     r"\b(?:donor|alumni|special|stewardship|recognition) events?\b|stewardship",
     "stewardship and special events"),
    ("student organization fundraising", r"student (?:org|club|group|chapter)",
     "student organization fundraising"),
    ("gift agreements", r"gift agreements?", "gift agreement processing"),
    ("the Young Alumni Council", r"young alumni council", "Young Alumni Council"),
    ("the Tribology program", r"tribology", "Tribology program"),
    ("the Pulp and Paper Foundation", r"pulp (?:and|&) paper", "Pulp and Paper Foundation"),
    ("the Thomas Walter Center for Technology Management", r"thomas walter|technology management",
     "Thomas Walter Center"),
    ("Nuclear Power Generation Systems", r"nuclear", "Nuclear Power Generation Systems"),
]

TERRITORIES = re.compile(r"territories including (.+?)(?: and serves\b|\.)")


def _territories(details: str) -> list[str]:
    """Places a development officer covers, from "oversees territories including A, B and C"."""
    m = TERRITORIES.search(details)
    if not m:
        return []
    places = re.split(r",\s*(?:and\s+)?|\s+and\s+", re.sub(r"\s*\([^)]*\)", "", m.group(1)))
    return [p.strip() for p in places if p.strip()]


def build_routes() -> tuple[list[dict], list[str]]:
    """Return (routes, unmatched). A route is {"topic", "pattern", "people"}; unmatched lists the
    PROGRAM_ROUTES topics whose directory phrase no longer appears in anyone's entry."""
    staff = _staff_records()
    routes, unmatched = [], []
    for kw, people in _liaisons().items():
        pattern = DEPARTMENT_ALIASES.get(kw, re.escape(kw))
        name = "Computer Science and Software" if kw == "computer science" else kw.title()
        routes.append({"topic": f"the {name} Engineering department", "people": people,
                       "pattern": re.compile(pattern, re.I)})
    for topic, pattern, phrase in PROGRAM_ROUTES:
        people = [p for p in staff if phrase.lower() in p["details"].lower()]
        if people:
            routes.append({"topic": topic, "people": people, "pattern": re.compile(pattern, re.I)})
        else:
            unmatched.append(topic)
    for p in staff:
        for place in _territories(p["details"]):
            routes.append({"topic": f"donors in {place}", "people": [p],
                           "pattern": re.compile(rf"\b{re.escape(place)}\b", re.I)})
    return routes, unmatched


class Router:
    def __init__(self):
        self.routes, self.unmatched = build_routes()

    def route(self, question: str) -> list[dict]:
        """Matches for a question that asks for a person: [{"topic", "people"}], else []."""
        if not CONTACT_INTENT.search(question):
            return []
        return [{"topic": r["topic"], "people": r["people"]}
                for r in self.routes if r["pattern"].search(question)]


def as_hit(match: dict, distance: float) -> dict:
    """A routing match in the shape of a retrieved chunk, so it joins the model's context."""
    slug = re.sub(r"[^A-Z0-9]+", "-", match["topic"].upper()).strip("-")
    people = "; ".join(_contact(p) for p in match["people"])
    return {"id": f"ROUTE-{slug}", "title": f"Contact for {match['topic']}",
            "text": f"Visitors asking who to talk to about {match['topic']} should be directed to "
                    f"this Engineering Advancement contact: {people}.",
            "distance": distance, "sources": [STAFF_DIRECTORY_URL]}


def direct_answer(matches: list[dict]) -> str:
    """The routed contacts as a plain sentence each, for when the model declines to name them."""
    return " ".join(
        f"The Engineering Advancement contact for {m['topic']} is "
        + " or ".join(_contact(p) for p in m["people"]) + "."
        for m in matches)


def contact_cards(matches: list[dict]) -> list[dict]:
    """The routed staff, once each, as the widget's contact cards."""
    cards = {}
    for m in matches:
        for p in m["people"]:
            cards.setdefault(p["name"], {"name": p["name"], "title": p["title"],
                                         "email": p["email"], "phone": p["phone"],
                                         "topic": m["topic"]})
    return list(cards.values())


if __name__ == "__main__":
    routes, unmatched = build_routes()
    for r in routes:
        print(f"{r['topic']:55} -> {', '.join(p['name'] for p in r['people'])}")
    for topic in unmatched:
        print(f"NO MATCH in the staff directory for: {topic}")
    missing = [kw for kw in DEPARTMENT_KEYWORDS if kw not in _liaisons()]
    print(f"\n{len(routes)} routes. Departments with no listed liaison: {', '.join(missing) or 'none'}")
