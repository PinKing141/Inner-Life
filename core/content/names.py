"""Name pools by gender. Trivial today; later this should be regionalised by
country and era so a 1962 UK character doesn't get a 2020 American name."""

NAMES: dict[str, list[str]] = {
    "Male": [
        "Oliver", "George", "Arthur", "Noah", "Muhammad",
        "Leo", "Oscar", "Harry", "Jack", "Henry",
    ],
    "Female": [
        "Olivia", "Amelia", "Isla", "Ava", "Ivy",
        "Freya", "Lily", "Florence", "Mia", "Willow",
    ],
    "NonBinary": [
        "Alex", "Jordan", "Charlie", "Sam", "Taylor",
        "Morgan", "Casey", "Riley", "Quinn", "Rowan",
    ],
}

COUNTRIES = ["United Kingdom", "United States", "Australia", "Canada", "Japan"]

TALENTS = ["Sports", "Music", "Academics", "Crime", "Acting"]
