# US-Macro-MCP

<!-- mcp-name: io.github.hgus107/us-macro-mcp -->

An MCP server that gives AI assistants clean access to US macroeconomic data — 58 indicators covering inflation, employment, growth, housing, consumer behaviour, interest rates, financial stress, markets and federal finances, sourced from the Federal Reserve's FRED database.

It is built so the assistant never has to know a FRED series ID, and never has to do arithmetic. Ask for `cpi` and you get the latest reading, the previous one, the year-ago value, and the percentage changes already calculated.

Registry Official Link : https://pypi.org/project/us-macro-mcp/

## Changelog

| Date | Version | Comment |
|---|---|---|
| 2026-07-27 | 0.1.2 | Added OS and Python version classifiers, changelog, and contact address switched to GitHub noreply. |
| 2026-07-27 | 0.1.1 | Added `mcp-name` marker for registry ownership verification. First version listed in the official MCP registry. |
| 2026-07-27 | 0.1.0 | Initial release — 58 indicators, 8 tools. Yanked; superseded by 0.1.1. |

## What it does

| Tool | What you use it for |
|---|---|
| `list_indicators` | See every indicator available, grouped by category |
| `get_indicator` | The current reading of one indicator, with its changes |
| `get_history` | A full time series, for trends and charting |
| `compare_indicators` | Two or more indicators over the same window, normalised for comparison |
| `release_calendar` | Which economic reports are scheduled over the coming days |
| `macro_snapshot` | The whole economy — or one category — in a single call |
| `recession_signals` | The Sahm rule, yield curve, credit spreads, claims and financial conditions, each graded |
| `search_indicators` | Find an indicator by keyword when you don't know its name |

## Requirements

A free FRED API key. Request one at [fredaccount.stlouisfed.org/apikeys](https://fredaccount.stlouisfed.org/apikeys) — it takes about a minute and costs nothing.

## Install

### Codex plugin marketplace

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and make sure
`uvx` is on the PATH available to Codex. The plugin launches the published PyPI
release `us-macro-mcp==0.1.2` locally over stdio; it requires Python 3.10 or newer.
Its launcher constrains the MCP SDK to `>=1.2,<2` because this release uses the
SDK's v1 FastMCP API.

1. Make your `FRED_API_KEY` environment variable available to the Codex app before
   starting it. The plugin forwards that variable to the MCP server; it does not
   store the key in its files or prompt for it during installation.
   On macOS, run this locally, then fully quit and reopen Codex:

   ```bash
   launchctl setenv FRED_API_KEY 'YOUR_FRED_API_KEY'
   ```

   Replace the placeholder with your own key. Do not commit or share the key.
   `launchctl setenv` applies to the current login session; repeat it after logging
   back in. On Linux, export the variable before launching Codex from that shell;
   on Windows, set a user environment variable and restart Codex.
2. In Codex, open **Plugins → Add → Add plugin marketplace**.
3. Set **Source** to `Signal-Drifts/US-Macro-MCP` (or
   `https://github.com/Signal-Drifts/US-Macro-MCP.git`), set **Git ref** to `main`,
   leave **Sparse paths** empty, and click **Add marketplace**.
4. Select **Signal Drifts** and install **US Macro**, then start a new chat.
5. Try: “Use US Macro to list the available indicators,” then ask for a macro
   snapshot. Listing indicators checks discovery; live data also requires the
   FRED key and network access to FRED.

You can also register the marketplace with the Codex CLI:

```bash
codex plugin marketplace add Signal-Drifts/US-Macro-MCP --ref main
```

The catalog is at `.agents/plugins/marketplace.json`; the plugin manifest and MCP
configuration are under `plugins/us-macro-mcp/`. The plugin package has its own
version: plugin `0.1.4` uses PyPI server `0.1.2`. When updating the server release,
update the pinned PyPI version in the plugin's `.mcp.json` and bump the plugin
manifest version, then refresh the marketplace and installed plugin.

This repository provides a custom marketplace. Inclusion in OpenAI's public
plugin directory is a separate submission and review process; local MCP
submissions currently require an approved partner organization. See the official
[plugin packaging guide](https://developers.openai.com/plugins/build/plugins) and
[desktop-only submission guide](https://developers.openai.com/plugins/deploy/desktop-only).

The existing MCP Registry identifier `io.github.hgus107/us-macro-mcp` is retained;
moving the GitHub repository does not migrate that registry identity. Repository
links in future Python/MCP Registry releases point to `Signal-Drifts`; metadata
already published on PyPI remains attached to its existing release.

### Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "us-macro": {
      "command": "uvx",
      "args": ["--from", "us-macro-mcp==0.1.2", "--with", "mcp[cli]>=1.2,<2", "us-macro-mcp"],
      "env": { "FRED_API_KEY": "your_key_here" }
    }
  }
}
```

### Claude Code

```bash
claude mcp add us-macro --env FRED_API_KEY=your_key_here -- uvx --from us-macro-mcp==0.1.2 --with 'mcp[cli]>=1.2,<2' us-macro-mcp
```

### Any other MCP client

With `FRED_API_KEY` set in the environment, run:

```bash
uvx --from us-macro-mcp==0.1.2 --with 'mcp[cli]>=1.2,<2' us-macro-mcp
```

The server speaks MCP over stdio.

## How it behaves

**It runs locally.** Nothing is hosted. Your client launches the server as a subprocess on your own machine, using your own API key. No data leaves your computer except the read-only requests to FRED.

**It caches.** A single `macro_snapshot` fetches 19 indicators at once, and conversations tend to ask for the same series repeatedly. Answers are held in memory for a period matched to how often the number can actually change — an hour for daily series like Treasury yields, half a day for monthly series like CPI. The cache is discarded when the process exits. Adjust `CACHE_SECONDS` in `fred.py` if you want different behaviour.

**It never logs your API key.** Requests are logged as endpoint, series and status code only, and any error text is stripped of the key before it is written or returned.

## Known limitations

- **The ISM Manufacturing and Services PMI are not available.** ISM licenses its data commercially and withdrew it from FRED. The same applies to the Conference Board Consumer Confidence Index. There is no free source for either.
- **Rates are national averages, not per-bank.** The 30-year mortgage rate is Freddie Mac's weekly survey across thousands of lenders — not any particular bank's advertised rate. Per-institution rates are not published free by anyone.
- **FOMC meeting dates are not included.** FRED publishes data release schedules, not the Federal Reserve's meeting calendar.
- **Michigan consumer sentiment lags.** As of this writing FRED's `UMCSENT` and `MICH` series are running about two months behind other monthly indicators. The `latest_date` field always tells you what you actually got.
- **Data is reported for the period it covers.** June CPI is dated `2026-06-01` and publishes in mid-July. Always read `latest_date` rather than assuming the most recent month exists yet.

## Data source and disclaimer

All data comes from [FRED](https://fred.stlouisfed.org/), maintained by the Federal Reserve Bank of St. Louis, which aggregates it from the Bureau of Labor Statistics, the Bureau of Economic Analysis, the Census Bureau, the Federal Reserve Board and others.

The `recession_signals` tool applies well-known statistical thresholds to public data. It is not a forecast, and nothing this server returns is investment advice.

## Annual maintenance checklist

The Federal Reserve publishes its meeting schedule about two years ahead, and Python, the MCP SDK and
FRED's own catalog all drift over a year. Work through this list every January and cut a new release.

**Data**

- [ ] Refresh the FOMC schedule in `src/us_macro_mcp/fomc.py` from
      [federalreserve.gov/monetarypolicy/fomccalendars.htm](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm),
      and move `VALID_THROUGH` forward. The `next_fomc_meeting` field goes empty once the list runs out.
- [ ] Re-validate every series ID in the catalog. FRED retires series without warning — the ADP
      employment series was discontinued this way, returning a valid response with zero observations:

      cd ~/Downloads/Apps/US-Macro-MCP && uv run python -c "
      import asyncio, logging
      logging.getLogger('us_macro_mcp').setLevel(logging.WARNING)
      from us_macro_mcp import catalog, fred
      async def main():
          sem = asyncio.Semaphore(8)
          async def check(i):
              async with sem:
                  try:
                      p = await fred.get_observations(i.series_id, start='2025-01-01', frequency_hint=i.frequency)
                      return (i.name, 'OK' if p else 'EMPTY', p[-1]['date'] if p else '-')
                  except Exception as e:
                      return (i.name, 'FAIL: ' + str(e)[:70], '-')
          rows = await asyncio.gather(*(check(i) for i in catalog.CATALOG))
          print('problems:', [r for r in rows if r[1] != 'OK'])
      asyncio.run(main())
      "

- [ ] Check whether anything previously unavailable has become free — particularly the ISM PMI and the
      Conference Board Consumer Confidence Index, both currently absent from FRED.
- [ ] Check FRED's API terms and rate limit (currently 120 requests per minute per key) for changes.

**Dependencies**

- [ ] Bump the `mcp` SDK and read its changelog for breaking changes. FastMCP is part of the official
      SDK, so a major version there can change how tools are declared or how the server starts.
- [ ] Check whether the MCP specification has revised its transports or tool schema.
- [ ] Bump `httpx`.
- [ ] Review `requires-python`. Drop versions that have reached end of life, and confirm the current
      floor still installs cleanly.

**Release**

- [ ] Run the full test sweep: all eight tools, plus the negative and boundary cases.
- [ ] Bump the version in `pyproject.toml` and in `server.json`. They must match or the registry
      rejects the publish.
- [ ] `uv build` and `uv publish` to PyPI.
- [ ] `mcp-publisher publish` to the official MCP registry.
- [ ] Tag the release on GitHub.

## License

MIT

## Support and policies

- [Support and bug reports](https://github.com/Signal-Drifts/US-Macro-MCP/issues)
- [Privacy policy](PRIVACY.md)
- [Software and data terms](TERMS.md)
