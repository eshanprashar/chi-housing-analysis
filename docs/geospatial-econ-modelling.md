# Geospatial Economic Reasoning — A Feature & Data-Source Framework

A framework for characterizing the economic life of a *place* from spatial data: what a location has, who is there, what they earn and spend, how reachable it is, how it is governed, what threatens it, and what it is worth.

This is distinct from **spatial reasoning** in the Fei-Fei Li / world-model sense (object- and scene-scale physical AI — geometry, materials, contact dynamics). Here the governing laws are *economic and behavioral* (accessibility, agglomeration, discrete choice), the unit is a place on the map, and the timescale is months to years.

---

## How to read this framework — four cross-cutting dimensions

1. **Accessibility is an operator, not only a bucket.** Most features have an *in-place* value and an *access-weighted* value (jobs *here* vs. jobs *reachable in 30 min*). Treat proximity/reachability as a spatial transform you can apply across buckets.
2. **Every feature has a level, a trajectory, and a volatility.** The *change* features are usually more predictive of development outcomes than the static snapshot.
3. **Separate drivers from capitalized outcomes.** Prices and rents capitalize almost everything else (schools, access, amenities). The Market-State bucket is mostly the *dependent variable* — quarantine it from the predictors to avoid leakage.
4. **Public/collective provision vs. private market consumption.** This line separates Infrastructure & Public Services (collectively provided, free at point of use) from Amenities (private, paid per use). For ambiguous items: *access/provision* → public services; *quality/desirability* → amenity.

A note on sourcing: a free federal/research backbone covers most buckets; commercial overlays buy **granularity** (point/parcel vs. tract), **recency** (real-time vs. annual), and **behavioral signal** (what people *do*, not who they are). `[free]` = public domain or free research data; `[paid]` = licensed.

---

## 1. Natural Environment & Physical Geography (endowments)

| Feature | Question the data answers | Sources |
|---|---|---|
| Terrain & elevation | Is the land flat or sloped — and how buildable is it? | USGS 3DEP / DEM `[free]` |
| Hydrology & water | Is there water nearby, and is it an amenity or a flood threat? | USGS NHD; USFWS National Wetlands Inventory `[free]` |
| Land cover & tree canopy | How green versus paved is this place? | MRLC NLCD; NDVI via Landsat/Sentinel (Google Earth Engine) `[free]` |
| Protected & open space | How much land here is preserved or undevelopable? | USGS PAD-US `[free]` |
| Climate | What weather do you live with year-round? | PRISM; NOAA NCEI `[free]` |
| Air quality | Is the air clean or polluted? | EPA AQS / AirNow `[free]` |

## 2. Built Environment & Land (endowments)

| Feature | Question the data answers | Sources |
|---|---|---|
| Parcels & property characteristics | What is built on each lot, and how old and large is it? | County assessors `[free, fragmented]`; Regrid, Cotality, ATTOM `[paid]` |
| Building footprints & heights | How dense and tall is the built form? | Overture, Microsoft Building Footprints, OSM `[free]` |
| Land use | What is this land currently used for? | NLCD `[free]`; local land-use GIS `[free, fragmented]` |
| Permits & pipeline | What is about to get built here? | Census Building Permits Survey `[free]`; Dodge, Construction Monitor `[paid]` |
| Zoning | What is legally allowed to be built here? | National Zoning Atlas (partial), local portals `[free, fragmented]`; Zoneomics `[paid]` |

## 3. Source of Money (economic activity / production — *workplace-located*)

| Feature | Question the data answers | Sources |
|---|---|---|
| Jobs by sector | Where are the jobs, and in which industries? | LEHD LODES (block-level), County Business Patterns, BLS QCEW `[free]` |
| Establishments | How many businesses operate here, and of what kind? | County / ZIP Business Patterns `[free]`; Data Axle, Dun & Bradstreet `[paid]` |
| Output & local GDP | How much economic value does this area produce? | BEA Regional `[free]` |
| Commercial activity / foot traffic | How busy is commerce here, in practice? | Placer.ai, Advan `[paid]` |

## 4. Income (purchasing power — *residence-located*)

| Feature | Question the data answers | Sources |
|---|---|---|
| Household income | How much do residents earn? | Census ACS; IRS SOI ZIP-level income `[free]` |
| Wealth & financial capacity | How much wealth and spending power do households hold? | Esri; Equifax / Experian small-area `[paid]` |
| Spending | What do households spend on, and how much? | BLS Consumer Expenditure Survey `[free]`; Esri / Claritas modeled, card panels `[paid]` |
| Cost of living | How expensive is it to live here? | BEA Regional Price Parities `[free]`; C2ER `[paid]` |

## 5. Amenities (private consumption + quality of place — *venue-located*)

| Feature | Question the data answers | Sources |
|---|---|---|
| Points of interest | What stores, restaurants, and venues exist here? | Overture, Foursquare Open Places, OSM `[free]`; Google Places, Data Axle `[paid]` |
| Utilization & spend | They exist — but how much are they actually *used* and spent at? | Card-spend panels: Mastercard, Affinity, Facteus, Earnest `[paid]`; retailer loyalty (Kroger / 84.51°) `[paid / partner]`; visits: Placer.ai, Advan `[paid]` |
| School quality | How good are the schools? | NCES, Stanford SEDA `[free]`; GreatSchools `[paid]` |
| Cultural & tourist draw | What is worth visiting here? | IMLS, Overture / OSM `[free]`; visitation via Placer `[paid]` |

## 6. Infrastructure & Public Services (collectively provided)

**Reachability**

| Feature | Question the data answers | Sources |
|---|---|---|
| Road network | How well is this place connected by road? | OSM, Census TIGER `[free]`; HERE / TomTom routing `[paid]` |
| Transit | Can you get around without a car? | GTFS feeds `[free]` |
| Accessibility & walkability | How much can you reach quickly from here? | EPA Smart Location Database `[free]`; routing via OSRM / Valhalla / r5 `[free]`; Walk Score `[paid]` |
| Broadband | Is there fast, available internet? | FCC National Broadband Map; Ookla / M-Lab `[free]` |
| Freight access | How connected is this for moving goods? | FHWA Freight Analysis Framework `[free]` |

**Site servicing**

| Feature | Question the data answers | Sources |
|---|---|---|
| Utilities (power / water / sewer) | Is the site actually served — and with what capacity? | HIFLD, EIA `[free]`; capacity often local-only `[fragmented]` |
| Healthcare access | Can residents reach medical care? | HRSA, CMS `[free]` |
| Parks access | Do residents have parks within reach? | Trust for Public Land ParkServe, USGS PAD-US `[free]` |
| Waste & sanitation | Is waste collection and disposal handled? | Municipal `[free, fragmented]`; EPA facilities `[free]` |

## 7. Institutions, Governance & Fiscal (rules)

| Feature | Question the data answers | Sources |
|---|---|---|
| Property tax | What does it cost to hold property here? | Tax Foundation `[free]`; assessor data via Cotality / ATTOM `[paid]` |
| Public finance | How much does local government spend, and on what? | Census of Governments / State & Local Finances `[free]` |
| Crime & safety | How safe is this place? | FBI NIBRS, city open-data portals `[free, uneven]` |
| Regulatory stringency | How hard is it to build here? | Wharton WRLURI; National Zoning Atlas `[free]` |
| Incentive zones | Are there tax or development incentives? | Treasury Opportunity Zones, HUD `[free]` |

## 8. Risk & Resilience (threats)

| Feature | Question the data answers | Sources |
|---|---|---|
| Multi-hazard exposure | What is the overall natural-hazard risk? | FEMA National Risk Index `[free]` |
| Flood | How likely is flooding? | FEMA NFHL `[free]`; First Street (climate-adjusted) `[paid]` |
| Wildfire & seismic | What is the fire and earthquake risk? | USFS Wildfire Risk to Communities, USGS `[free]` |
| Contamination | Is the land or environment contaminated? | EPA Superfund / NPL, Brownfields, TRI `[free]` |
| Insurance | How costly and available is insurance? | Cotality, Verisk `[paid]`; state DOI filings `[free, fragmented]` |

## 9. Market State (capitalized outcome — *quarantine as target, not predictor*)

| Feature | Question the data answers | Sources |
|---|---|---|
| Values & rents | What does property cost to buy or rent? | Zillow ZHVI / ZORI, Redfin, FHFA HPI `[free]`; Cotality HPI `[paid]` |
| Transactions | How much is changing hands, and at what price? | County recorder `[free, fragmented]`; Cotality, ATTOM `[paid]` |
| Listing velocity | How hot is the market right now? | Realtor.com research, Zillow, Redfin `[free]`; MLS `[licensed]` |
| Commercial real estate | What is the commercial property market like? | CoStar `[paid, dominant]`; Cotality `[paid]` |

---

## Where the effort actually goes

Roughly seven of the nine buckets are fully servable from free federal/research data (Natural Environment, Source of Money, Income, Reachability, Risk, Fiscal, Market trends). Commercial spend concentrates in four places: **parcels, behavioral signal** (foot traffic / card spend / visitation), **wealth, and commercial real estate**. The hardest work is not cost but *fragmentation* — zoning, utility/site-servicing capacity, property tax, and crime have no clean national free source and must be assembled jurisdiction by jurisdiction.