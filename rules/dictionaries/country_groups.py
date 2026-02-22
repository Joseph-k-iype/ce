"""
Country Groups Dictionary
=========================
Developers can add/modify country groups here.
Each group is a set of country names that can be referenced in rules.
"""

from typing import Dict, Set, FrozenSet

# EU/EEA Member States (EU 27 + EEA: Norway, Iceland, Liechtenstein)
EU_EEA_COUNTRIES: FrozenSet[str] = frozenset({
    "Belgium", "Bulgaria", "Czechia", "Denmark", "Germany", "Estonia",
    "Ireland", "Greece", "Spain", "France", "Croatia", "Italy", "Cyprus",
    "Latvia", "Lithuania", "Luxembourg", "Hungary", "Malta", "Netherlands",
    "Austria", "Poland", "Portugal", "Romania", "Slovenia", "Slovakia",
    "Finland", "Sweden",
    "Norway", "Iceland", "Liechtenstein",
})

# UK and Crown Dependencies
UK_CROWN_DEPENDENCIES: FrozenSet[str] = frozenset({
    "United Kingdom", "Jersey", "Guernsey", "Isle of Man"
})

# Crown Dependencies Only (without UK)
CROWN_DEPENDENCIES: FrozenSet[str] = frozenset({
    "Jersey", "Guernsey", "Isle of Man"
})

# Switzerland
SWITZERLAND: FrozenSet[str] = frozenset({"Switzerland"})

# EU Adequacy Countries (as of latest adequacy decisions, incl. US Data Privacy Framework)
ADEQUACY_COUNTRIES: FrozenSet[str] = frozenset({
    "Andorra", "Argentina", "Canada", "Faroe Islands", "Guernsey",
    "Israel", "Isle of Man", "Japan", "Jersey", "New Zealand",
    "Republic of Korea", "Switzerland", "United Kingdom", "Uruguay",
    "United States", "United States of America",
})

# Switzerland Approved Countries
SWITZERLAND_APPROVED: FrozenSet[str] = frozenset({
    "Andorra", "Argentina", "Canada", "Faroe Islands", "Guernsey",
    "Israel", "Isle of Man", "Jersey", "New Zealand", "Switzerland",
    "Uruguay", "Belgium", "Bulgaria", "Czechia", "Denmark", "Germany",
    "Estonia", "Ireland", "Greece", "Spain", "France", "Croatia",
    "Italy", "Cyprus", "Latvia", "Lithuania", "Luxembourg", "Hungary",
    "Malta", "Netherlands", "Austria", "Poland", "Portugal", "Romania",
    "Slovenia", "Slovakia", "Finland", "Sweden", "Gibraltar", "Monaco"
})

# BCR (Binding Corporate Rules) Countries
BCR_COUNTRIES: FrozenSet[str] = frozenset({
    "Algeria", "Australia", "Bahrain", "Bangladesh", "Belgium", "Bermuda",
    "Brazil", "Canada", "Cayman Islands", "Chile", "China", "Czech Republic",
    "British Virgin Islands", "Denmark", "Egypt", "France", "Germany",
    "Guernsey", "Hong Kong", "India", "Indonesia", "Ireland", "Isle of Man",
    "Italy", "Japan", "Jersey", "Korea, Republic Of (South)", "Kuwait",
    "Luxembourg", "Macao", "Malaysia", "Maldives", "Malta", "Mauritius",
    "Mexico", "Netherlands", "New Zealand", "Oman", "Philippines", "Poland",
    "Qatar", "Saudi Arabia", "Singapore", "South Africa", "Spain", "Sri Lanka",
    "Sweden", "Switzerland", "Taiwan", "Thailand", "Turkiye", "Turkey",
    "United Arab Emirates", "United Kingdom", "United States of America",
    "United States", "Uruguay", "Vietnam"
})

# Combined Groups (computed)
EU_EEA_UK_CROWN_CH: FrozenSet[str] = EU_EEA_COUNTRIES | UK_CROWN_DEPENDENCIES | SWITZERLAND
EU_EEA_ADEQUACY_UK: FrozenSet[str] = EU_EEA_COUNTRIES | ADEQUACY_COUNTRIES
ADEQUACY_PLUS_EU: FrozenSet[str] = ADEQUACY_COUNTRIES | EU_EEA_COUNTRIES

# Special marker for "any country"
ANY_COUNTRY: str = "__ANY__"

# Master registry of all country groups
COUNTRY_GROUPS: Dict[str, FrozenSet[str]] = {
    "EU_EEA": EU_EEA_COUNTRIES,
    "UK_CROWN_DEPENDENCIES": UK_CROWN_DEPENDENCIES,
    "CROWN_DEPENDENCIES": CROWN_DEPENDENCIES,
    "SWITZERLAND": SWITZERLAND,
    "ADEQUACY_COUNTRIES": ADEQUACY_COUNTRIES,
    "SWITZERLAND_APPROVED": SWITZERLAND_APPROVED,
    "BCR_COUNTRIES": BCR_COUNTRIES,
    "EU_EEA_UK_CROWN_CH": EU_EEA_UK_CROWN_CH,
    "EU_EEA_ADEQUACY_UK": EU_EEA_ADEQUACY_UK,
    "ADEQUACY_PLUS_EU": ADEQUACY_PLUS_EU,
}


def get_country_group(group_name: str) -> FrozenSet[str]:
    """Get a country group by name"""
    return COUNTRY_GROUPS.get(group_name, frozenset())


def is_country_in_group(country: str, group_name: str) -> bool:
    """Check if a country belongs to a group"""
    group = COUNTRY_GROUPS.get(group_name, frozenset())
    return country in group


def get_all_countries() -> Set[str]:
    """Get all unique countries from all groups"""
    all_countries: Set[str] = set()
    for group in COUNTRY_GROUPS.values():
        all_countries.update(group)
    return all_countries
