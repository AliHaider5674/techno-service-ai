"""Simulated data sources for Continuous Proactive Discovery.

Per the Sprint Brief, the default data source is SIMULATED. Every
result is clearly marked with the data source identifier and the
DEMO_DATA marker. Real data sources (USPTO, OpenCorporates, etc.)
are added later when API keys are available — the DataSource
interface is ready.

Constitutional constraint:
  The system MUST NEVER present simulated data as if it were real.
  Every candidate record carries:
    - data_source       (e.g. "SIMULATED", "USPTO")
    - data_source_marker ("DEMO_DATA" or "REAL")
  If the data source is unknown or the marker is missing, the
  candidate is REJECTED at the register layer.

This module is pure logic, no DB coupling.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


# The default data source identifier.
DEFAULT_DATA_SOURCE = "SIMULATED"
DEMO_DATA_MARKER = "DEMO_DATA"
REAL_DATA_MARKER = "REAL"

# Recognised real data sources (interfaces ready; implementations
# added later when API keys are available). These are the only
# identifiers that may be marked as REAL.
KNOWN_REAL_SOURCES = frozenset({"USPTO", "OPEN_CORPORATES", "TRADE_PUB"})

# All known sources (real + simulated).
KNOWN_SOURCES = frozenset({DEFAULT_DATA_SOURCE} | KNOWN_REAL_SOURCES)


class DataSourceMarker(str, Enum):
    DEMO_DATA = "DEMO_DATA"
    REAL = "REAL"


@dataclass
class SourceCandidate:
    """A raw candidate as produced by a data source.

    Distinct from the constitutional ProactiveProductDiscovery.
    This is the raw form returned by a data source before the
    5 filters are applied.
    """

    product_name: str
    product_category: str
    sector: str
    manufacturer_name: str
    manufacturer_country: Optional[str] = None
    source_citation_url: Optional[str] = None
    signal_strength: str = "MEDIUM"  # HIGH / MEDIUM / LOW
    data_source: str = DEFAULT_DATA_SOURCE
    data_source_marker: str = DEMO_DATA_MARKER


class DataSource:
    """Interface for any Continuous Proactive Discovery data source.

    Implementations must:
      - Carry a stable `name` (e.g. "SIMULATED", "USPTO").
      - Carry a `marker` (DEMO_DATA or REAL).
      - Implement `fetch_candidates()` to return a list of
        SourceCandidate objects. The list may be empty.
    """

    name: str = ""
    marker: str = DEMO_DATA_MARKER

    def fetch_candidates(self, max_n: int = 5) -> List[SourceCandidate]:  # noqa: D401
        raise NotImplementedError


class SimulatedDataSource(DataSource):
    """Default data source. Produces realistic-looking candidates for
    the demo. Always marked DEMO_DATA.

    The simulated candidates are inspired by the product domain in
    Document 02 §4.18 (industrial maintenance, oil & gas, water
    treatment, HVAC, electrical, instrumentation). Manufacturer
    names are FICTIONAL — they do not represent real companies.
    """

    name = DEFAULT_DATA_SOURCE
    marker = DEMO_DATA_MARKER

    # Fictional product catalog (clearly DEMO). Manufacturer names
    # are invented and do not correspond to real companies.
    _CATALOG = [
        {
            "product_name": "Acme Heat-Resistant Submersible Pump 5HP",
            "product_category": "INDUSTRIAL_MAINTENANCE",
            "sector": "OIL_GAS",
            "manufacturer_name": "Acme Pump Works (Demo)",
            "manufacturer_country": "Italy",
            "signal_strength": "HIGH",
        },
        {
            "product_name": "BlueWave Sand Filter System 20m3/h",
            "product_category": "WATER_TREATMENT",
            "sector": "MUNICIPAL",
            "manufacturer_name": "BlueWave Aqua (Demo)",
            "manufacturer_country": "Germany",
            "signal_strength": "MEDIUM",
        },
        {
            "product_name": "DustKing Industrial Dust Collector 5000 CFM",
            "product_category": "INDUSTRIAL_MAINTENANCE",
            "sector": "CEMENT",
            "manufacturer_name": "DustKing Tech (Demo)",
            "manufacturer_country": "Türkiye",
            "signal_strength": "MEDIUM",
        },
        {
            "product_name": "HeliCal PV Solar Tracker Single-Axis",
            "product_category": "ENERGY",
            "sector": "RENEWABLE",
            "manufacturer_name": "HeliCal Solar (Demo)",
            "manufacturer_country": "Spain",
            "signal_strength": "HIGH",
        },
        {
            "product_name": "IsoGuard Wireless Gas Detector H2S",
            "product_category": "INSTRUMENTATION",
            "sector": "OIL_GAS",
            "manufacturer_name": "IsoGuard Sensors (Demo)",
            "manufacturer_country": "Netherlands",
            "signal_strength": "HIGH",
        },
        {
            "product_name": "PowerFlex Variable Frequency Drive 75kW",
            "product_category": "ELECTRICAL",
            "sector": "MANUFACTURING",
            "manufacturer_name": "PowerFlex Drives (Demo)",
            "manufacturer_country": "Italy",
            "signal_strength": "MEDIUM",
        },
        {
            "product_name": "SandStorm Desert Solar Panel 600W",
            "product_category": "ENERGY",
            "sector": "RENEWABLE",
            "manufacturer_name": "SandSolar MENA (Demo)",
            "manufacturer_country": "UAE",
            "signal_strength": "MEDIUM",
        },
        {
            "product_name": "VentMax Hurricane-Rated Industrial Fan",
            "product_category": "HVAC",
            "sector": "OIL_GAS",
            "manufacturer_name": "VentMax Engineering (Demo)",
            "manufacturer_country": "Egypt",
            "signal_strength": "LOW",
        },
    ]

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    def fetch_candidates(self, max_n: int = 5) -> List[SourceCandidate]:
        """Return up to max_n random candidates from the catalog.

        The seed is set at construction time so test runs are
        deterministic. The citation URL is the SIMULATED marker
        — the UI must show this clearly.
        """
        n = min(max_n, len(self._CATALOG))
        chosen = self._rng.sample(self._CATALOG, k=n)
        results: List[SourceCandidate] = []
        for item in chosen:
            results.append(
                SourceCandidate(
                    product_name=item["product_name"],
                    product_category=item["product_category"],
                    sector=item["sector"],
                    manufacturer_name=item["manufacturer_name"],
                    manufacturer_country=item["manufacturer_country"],
                    source_citation_url=f"simulated://{item['manufacturer_name'].split()[0].lower()}/{item['product_name'][:32].replace(' ', '_').lower()}",
                    signal_strength=item["signal_strength"],
                    data_source=self.name,
                    data_source_marker=self.marker,
                )
            )
        return results


class DataSourceRegistry:
    """Registry of available data sources.

    The default registry contains only SimulatedDataSource. Real
    data sources are added when API keys are available.
    """

    def __init__(self) -> None:
        self._sources: dict = {}
        self.register(SimulatedDataSource())

    def register(self, source: DataSource) -> None:
        if not source.name:
            raise ValueError("DataSource.name must be set")
        if source.marker not in (DEMO_DATA_MARKER, REAL_DATA_MARKER):
            raise ValueError(f"DataSource.marker must be DEMO_DATA or REAL (got {source.marker!r})")
        if source.name not in KNOWN_SOURCES:
            raise ValueError(f"Unknown data source {source.name!r}; expected one of {KNOWN_SOURCES}")
        self._sources[source.name] = source

    def get(self, name: str) -> DataSource:
        if name not in self._sources:
            raise KeyError(f"Data source {name!r} not registered; available: {sorted(self._sources)}")
        return self._sources[name]

    def available(self) -> List[str]:
        return sorted(self._sources)


# Module-level singleton registry.
_REGISTRY = DataSourceRegistry()


def get_default_registry() -> DataSourceRegistry:
    return _REGISTRY


def get_default_data_source() -> DataSource:
    return _REGISTRY.get(DEFAULT_DATA_SOURCE)
