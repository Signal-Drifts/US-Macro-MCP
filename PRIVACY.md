# US Macro privacy policy

Effective date: October 26, 2026

US Macro is the open-source US-Macro-MCP server and its plugin package, maintained
by Harish Gupta through the Signal Drifts GitHub organization. This policy
describes the distributed local server. The maintainer does not operate a hosted
query endpoint for this version.

## Information processed and why

- **Tool inputs:** The server processes indicator names, search keywords,
  categories, date ranges and other tool parameters to find and return economic
  data. Its tools do not request a full chat transcript, identity documents,
  contact details or payment information.
- **FRED API key:** The server reads your key from its environment or a local
  `.env` file. It sends the key to FRED over HTTPS to authenticate data requests.
  The server does not send it to the maintainer. Request logging excludes the
  full request URL, and the server redacts the key from its error messages.
- **Economic data and operational messages:** Results are returned to your MCP
  client. The server can write endpoint names, series identifiers, HTTP status
  codes and redacted errors to local standard error for troubleshooting.

The distributed server has no query-analytics, advertising or tracking endpoint
that sends information to the maintainer. It does not require a separate US
Macro account.

## Recipients and third-party services

FRED receives the data requests, API key and the network information ordinarily
available to a server, such as your IP address and request time. Its practices
are described in the [Federal Reserve Bank of St. Louis privacy
policy](https://www.stlouisfed.org/policies/privacy-policy).

Your MCP client, including ChatGPT or Codex when used, receives tool inputs and
results and may retain chats, tool activity or local logs according to its own
settings and policies. Installing or launching through `uv` can contact PyPI and
other package or runtime distribution services to download dependencies. GitHub
hosts the repository, documentation and issue tracker. These services operate
under their own privacy policies; this policy does not set their retention rules.

## Retention

The server keeps fetched economic data in process memory to reduce repeated
requests. Cache entries expire according to the series frequency: generally one
hour for daily data, six hours for weekly data, twelve hours for monthly and
quarterly data, and twenty-four hours for annual data and metadata. The cache is
discarded when the process exits. The API key remains available to the running
process while configured.

The server does not write a persistent database or log file. A client may capture
standard error or save tool results; retention of those copies is controlled by
that client. A key you place in an environment setting or `.env` file remains
there until you remove it. Information you voluntarily post in a GitHub issue is
public and retained according to GitHub's policies and repository moderation.

## Your controls and contact

You can disable or uninstall the plugin, stop the server to clear its memory
cache, remove your locally configured key, and revoke the key through your FRED
account. Manage retained conversations and captured logs through your MCP client.

For privacy questions, use the [project issue
tracker](https://github.com/Signal-Drifts/US-Macro-MCP/issues). Do not post API keys,
identity documents or other private information in public issues. Report a
possible key exposure privately using the [security reporting
instructions](https://github.com/Signal-Drifts/US-Macro-MCP/blob/main/SECURITY.md).

Changes to this policy are recorded in this repository's version history.
