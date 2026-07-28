"""
The indicator catalog for US-Macro-MCP.

What this file does, in order:
1. Defines one Indicator record per economic statistic we support - its friendly
   name, its FRED series ID, which category it belongs to, and how often it updates.
2. Lists all 58 indicators, grouped by category, in the CATALOG tuple.
3. Builds lookup dictionaries so the rest of the program can find an indicator
   by its friendly name (for example "cpi") or by its FRED series ID.
4. Provides small helper functions to search the catalog and to list the categories.
"""

from __future__ import annotations

from dataclasses import dataclass

# One economic indicator: the friendly name users ask for, plus everything we need to fetch and label it.
@dataclass(frozen=True)
class Indicator:
    name: str           # friendly name used in tool arguments, e.g. "core_cpi"
    series_id: str      # the FRED series ID we actually request, e.g. "CPILFESL"
    title: str          # human-readable title shown in results
    category: str       # one of the CATEGORIES below
    units: str          # what the numbers mean, e.g. "Percent" or "Index 1982-84=100"
    frequency: str      # how often FRED updates it: Daily, Weekly, Monthly, Quarterly
    major: bool = False # True for headline indicators included in snapshots and the calendar
    notes: str = ""     # optional one-line explanation of how to read the number


CATEGORIES = (
    "inflation",
    "employment",
    "growth",
    "housing",
    "consumer",
    "rates",
    "stress",
    "markets",
    "fiscal",
)


CATALOG: tuple[Indicator, ...] = (
    # ---------------------------------------------------------------- inflation
    Indicator("cpi", "CPIAUCSL", "Consumer Price Index (All Items)", "inflation",
              "Index 1982-84=100", "Monthly", major=True,
              notes="Headline inflation; read the year-over-year percent change."),
    Indicator("core_cpi", "CPILFESL", "Core CPI (Excluding Food and Energy)", "inflation",
              "Index 1982-84=100", "Monthly", major=True,
              notes="Strips out volatile food and energy prices."),
    Indicator("pce", "PCEPI", "PCE Price Index", "inflation",
              "Index 2017=100", "Monthly",
              notes="The broader price measure the Federal Reserve prefers."),
    Indicator("core_pce", "PCEPILFE", "Core PCE Price Index", "inflation",
              "Index 2017=100", "Monthly", major=True,
              notes="The Federal Reserve's official 2 percent inflation target measure."),
    Indicator("ppi", "PPIFIS", "Producer Price Index (Final Demand)", "inflation",
              "Index 2009=100", "Monthly", major=True,
              notes="Prices producers receive; often leads consumer prices."),
    Indicator("breakeven_5y", "T5YIE", "5-Year Breakeven Inflation Rate", "inflation",
              "Percent", "Daily",
              notes="What the bond market expects inflation to average over 5 years."),
    Indicator("breakeven_10y", "T10YIE", "10-Year Breakeven Inflation Rate", "inflation",
              "Percent", "Daily"),

    # --------------------------------------------------------------- employment
    Indicator("unemployment_rate", "UNRATE", "Unemployment Rate", "employment",
              "Percent", "Monthly", major=True),
    Indicator("nonfarm_payrolls", "PAYEMS", "Total Nonfarm Payrolls", "employment",
              "Thousands of Persons", "Monthly", major=True,
              notes="Read the month-over-month change - that is the 'jobs number'."),
    Indicator("private_payrolls", "USPRIV", "All Employees, Total Private", "employment",
              "Thousands of Persons", "Monthly",
              notes="Jobs at private employers only - excludes government hiring."),
    Indicator("jobless_claims", "ICSA", "Initial Jobless Claims", "employment",
              "Number", "Weekly", major=True,
              notes="Weekly new unemployment filings; the fastest labor market signal."),
    Indicator("continuing_claims", "CCSA", "Continuing Jobless Claims", "employment",
              "Number", "Weekly",
              notes="People still collecting benefits; shows how hard it is to get rehired."),
    Indicator("job_openings", "JTSJOL", "Job Openings (JOLTS)", "employment",
              "Thousands", "Monthly", major=True),
    Indicator("labor_participation", "CIVPART", "Labor Force Participation Rate", "employment",
              "Percent", "Monthly"),
    Indicator("avg_hourly_earnings", "CES0500000003", "Average Hourly Earnings", "employment",
              "Dollars per Hour", "Monthly",
              notes="Wage growth; compare its year-over-year change against CPI."),

    # ------------------------------------------------------------------- growth
    Indicator("gdp", "GDPC1", "Real Gross Domestic Product", "growth",
              "Billions of Chained 2017 Dollars", "Quarterly", major=True,
              notes="Inflation-adjusted output; the headline growth number."),
    Indicator("gdp_nominal", "GDP", "Nominal Gross Domestic Product", "growth",
              "Billions of Dollars", "Quarterly"),
    Indicator("industrial_production", "INDPRO", "Industrial Production Index", "growth",
              "Index 2017=100", "Monthly"),
    Indicator("capacity_utilization", "TCU", "Capacity Utilization", "growth",
              "Percent of Capacity", "Monthly"),
    Indicator("durable_goods", "DGORDER", "Durable Goods New Orders", "growth",
              "Millions of Dollars", "Monthly",
              notes="Business orders for long-lasting goods; a capital spending gauge."),
    Indicator("productivity", "OPHNFB", "Nonfarm Business Labor Productivity", "growth",
              "Index 2017=100", "Quarterly"),
    Indicator("philly_fed", "GACDFSA066MSFRBPHI", "Philadelphia Fed Manufacturing Survey", "growth",
              "Diffusion Index", "Monthly",
              notes="Above zero means more factories reporting growth than decline."),
    Indicator("empire_state", "GACDISA066MSFRBNY", "Empire State Manufacturing Survey", "growth",
              "Diffusion Index", "Monthly",
              notes="New York Fed factory survey; the earliest monthly read on manufacturing."),
    Indicator("national_activity", "CFNAI", "Chicago Fed National Activity Index", "growth",
              "Index", "Monthly",
              notes="85 indicators combined; zero is average growth, negative is below trend."),

    # ------------------------------------------------------------------ housing
    Indicator("housing_starts", "HOUST", "Housing Starts", "housing",
              "Thousands of Units (Annual Rate)", "Monthly", major=True),
    Indicator("building_permits", "PERMIT", "Building Permits", "housing",
              "Thousands of Units (Annual Rate)", "Monthly",
              notes="Leads housing starts by a month or two."),
    Indicator("new_home_sales", "HSN1F", "New One-Family Home Sales", "housing",
              "Thousands of Units (Annual Rate)", "Monthly"),
    Indicator("existing_home_sales", "EXHOSLUSM495S", "Existing Home Sales", "housing",
              "Number of Units (Annual Rate)", "Monthly"),
    Indicator("home_prices", "CSUSHPINSA", "Case-Shiller National Home Price Index", "housing",
              "Index Jan 2000=100", "Monthly",
              notes="Reported with a two-month lag."),
    Indicator("mortgage_30y", "MORTGAGE30US", "30-Year Fixed Mortgage Rate", "housing",
              "Percent", "Weekly", major=True,
              notes="Freddie Mac national average, not any single lender's rate."),
    Indicator("mortgage_15y", "MORTGAGE15US", "15-Year Fixed Mortgage Rate", "housing",
              "Percent", "Weekly"),

    # ----------------------------------------------------------------- consumer
    Indicator("retail_sales", "RSAFS", "Retail and Food Services Sales", "consumer",
              "Millions of Dollars", "Monthly", major=True),
    Indicator("consumer_sentiment", "UMCSENT", "University of Michigan Consumer Sentiment", "consumer",
              "Index 1966Q1=100", "Monthly", major=True),
    Indicator("inflation_expectations", "MICH", "Michigan 1-Year Inflation Expectations", "consumer",
              "Percent", "Monthly",
              notes="What households think inflation will be over the next year."),
    Indicator("personal_income", "PI", "Personal Income", "consumer",
              "Billions of Dollars (Annual Rate)", "Monthly"),
    Indicator("personal_spending", "PCE", "Personal Consumption Expenditures", "consumer",
              "Billions of Dollars (Annual Rate)", "Monthly"),
    Indicator("savings_rate", "PSAVERT", "Personal Saving Rate", "consumer",
              "Percent of Disposable Income", "Monthly"),
    Indicator("consumer_credit", "TOTALSL", "Total Consumer Credit Outstanding", "consumer",
              "Billions of Dollars", "Monthly",
              notes="How much household borrowing is building up."),

    # -------------------------------------------------------------------- rates
    Indicator("fed_funds", "DFF", "Effective Federal Funds Rate", "rates",
              "Percent", "Daily", major=True,
              notes="The overnight rate the Federal Reserve steers with policy decisions."),
    Indicator("sofr", "SOFR", "Secured Overnight Financing Rate", "rates",
              "Percent", "Daily"),
    Indicator("treasury_3m", "DGS3MO", "3-Month Treasury Yield", "rates",
              "Percent", "Daily"),
    Indicator("treasury_2y", "DGS2", "2-Year Treasury Yield", "rates",
              "Percent", "Daily"),
    Indicator("treasury_10y", "DGS10", "10-Year Treasury Yield", "rates",
              "Percent", "Daily", major=True),
    Indicator("treasury_30y", "DGS30", "30-Year Treasury Yield", "rates",
              "Percent", "Daily"),
    Indicator("yield_curve", "T10Y2Y", "10-Year Minus 2-Year Treasury Spread", "rates",
              "Percent", "Daily", major=True,
              notes="Below zero is an inverted curve, historically a recession warning."),
    Indicator("fed_balance_sheet", "WALCL", "Federal Reserve Total Assets", "rates",
              "Millions of Dollars", "Weekly",
              notes="Shrinking means the Federal Reserve is draining liquidity."),

    # ------------------------------------------------------------------- stress
    Indicator("high_yield_spread", "BAMLH0A0HYM2", "High Yield Bond Spread", "stress",
              "Percent", "Daily", major=True,
              notes="Extra yield demanded on risky corporate debt; widens when credit is stressed."),
    Indicator("financial_conditions", "NFCI", "Chicago Fed National Financial Conditions Index", "stress",
              "Index", "Weekly",
              notes="Above zero means conditions are tighter than average."),
    Indicator("sahm_rule", "SAHMREALTIME", "Sahm Rule Recession Indicator", "stress",
              "Percentage Points", "Monthly", major=True,
              notes="At or above 0.50 has historically meant a recession has begun."),
    Indicator("lending_standards", "DRTSCILM", "Banks Tightening Business Lending Standards", "stress",
              "Net Percent of Banks", "Quarterly",
              notes="From the Fed's Senior Loan Officer Survey; rising means credit is getting harder to get."),

    # ------------------------------------------------------------------ markets
    Indicator("sp500", "SP500", "S&P 500 Index", "markets",
              "Index", "Daily", major=True),
    Indicator("vix", "VIXCLS", "CBOE Volatility Index (VIX)", "markets",
              "Index", "Daily",
              notes="Expected stock market volatility; spikes signal fear."),
    Indicator("dollar_index", "DTWEXBGS", "Trade Weighted US Dollar Index", "markets",
              "Index Jan 2006=100", "Daily"),
    Indicator("wti_crude", "DCOILWTICO", "WTI Crude Oil Price", "markets",
              "Dollars per Barrel", "Daily"),
    Indicator("gas_price", "GASREGW", "US Regular Gasoline Price", "markets",
              "Dollars per Gallon", "Weekly"),

    # ------------------------------------------------------------------- fiscal
    Indicator("federal_debt", "GFDEBTN", "Total Federal Public Debt", "fiscal",
              "Millions of Dollars", "Quarterly"),
    Indicator("federal_deficit", "MTSDS133FMS", "Federal Surplus or Deficit", "fiscal",
              "Millions of Dollars", "Monthly",
              notes="Negative values are deficits."),
    Indicator("debt_to_gdp", "GFDEGDQ188S", "Federal Debt as Percent of GDP", "fiscal",
              "Percent of GDP", "Quarterly"),
)


# Fast lookups built once at import: friendly name -> Indicator, and FRED series ID -> Indicator.
BY_NAME: dict[str, Indicator] = {item.name: item for item in CATALOG}
BY_SERIES_ID: dict[str, Indicator] = {item.series_id: item for item in CATALOG}


# Finds one indicator by friendly name, or by FRED series ID if the caller passed that instead.
def find(name: str) -> Indicator | None:
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    if key in BY_NAME:
        return BY_NAME[key]
    return BY_SERIES_ID.get(name.strip().upper())


# Returns every indicator in one category, or the whole catalog when no category is given.
def in_category(category: str | None) -> tuple[Indicator, ...]:
    if not category or category.lower() == "all":
        return CATALOG
    wanted = category.strip().lower()
    return tuple(item for item in CATALOG if item.category == wanted)


# Scores each indicator against a free-text query and returns the best matches first.
def search(query: str, limit: int = 10) -> list[Indicator]:
    words = [w for w in query.strip().lower().split() if w]
    if not words:
        return []

    scored: list[tuple[int, Indicator]] = []
    for item in CATALOG:
        haystack = " ".join(
            (item.name, item.title, item.category, item.notes, item.series_id)
        ).lower()
        score = 0
        for word in words:
            if word in item.name.lower():
                score += 3          # a hit on the friendly name is the strongest signal
            elif word in item.title.lower():
                score += 2          # a hit in the official title is next best
            elif word in haystack:
                score += 1          # a hit anywhere else still counts a little
        if score:
            scored.append((score, item))

    scored.sort(key=lambda pair: (-pair[0], pair[1].name))
    return [item for _, item in scored[:limit]]
