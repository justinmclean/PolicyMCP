# ASF Policy MCP

MCP server for answering questions about Apache Software Foundation policies.

Covers the full set of policies listed at <https://www.apache.org/board/policies> — releases, licensing, branding, security, infrastructure, incubator, and more.

Policy pages are cached locally for 30 days. Use `force_refresh=true` on read tools to bypass the cache for a single call.

## Install

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Run

```sh
asf-policy-mcp
```

For local development:

```sh
python -m asf_policy_mcp.server
```

## Test

```sh
pip install -e ".[dev]"
make check
```

## Configure with Claude Desktop or Codex

```json
{
  "mcpServers": {
    "asf-policy": {
      "command": "<path to PolicyMCP>/.venv/bin/python",
      "args": ["-m", "asf_policy_mcp.server"]
    }
  }
}
```

## Tools

- `list_policies` — list all available policy documents organised by section, with cache status.
- `get_policy` — retrieve the full text of a policy document by key (e.g. `release_policy`, `branding`, `incubator`).
- `search_policies` — keyword search across all policy documents, returning ranked excerpts with context.
- `refresh_cache` — force re-fetch of one or all policy documents from the ASF website.

## Example questions

**Releases**
- What files must be included in a release artifact for it to be valid?
- Can we ship a release with only one +1 vote from the PMC?
- Where must release artifacts be published — can we use GitHub Releases as the primary download?

**Incubator**
- What does a podling need to do before it can graduate?
- Can a podling cut a release before graduating, and what extra requirements apply?
- Who can vote on a podling release, and whose votes are binding?

**Licensing**
- Is the MIT licence compatible with Apache 2.0 for bundling in a release?
- Can we include a library licensed under LGPL 2.1?
- What is a Category X licence and why does it matter?
- Do we need a CLA from every contributor, or only committers?
- What licence headers are required in source files?

**Security**
- If someone reports a vulnerability privately, how long before we must disclose?
- Should security issues be discussed on the public dev list?

**Branding**
- Can a third party use "Apache Foo" in the name of their commercial product?
- What must appear on a project website for trademark compliance?

## Policy documents

| Key | Title | Section |
|---|---|---|
| `pmc` | PMC Guide | Community And Project Oversight |
| `project_independence` | Project Independence | Independence |
| `board_reporting` | Board Reporting Requirements | Reporting |
| `release_policy` | Release Policy | Release |
| `voting` | Apache Voting Process | Release |
| `release_distribution` | Release Distribution Policy | Release |
| `security` | Security Team Guidance | Security |
| `security_committers` | Vulnerability Handling for Committers | Security |
| `licenses` | Contributor License Agreements | Licensing |
| `source_headers` | Apache Source Headers | Licensing |
| `resolved_licenses` | Approved/Resolved Third-Party Licenses | Licensing |
| `branding` | Project Branding Requirements | Branding |
| `trademark_maintenance` | Trademark Maintenance Responsibilities | Branding |
| `website_linking` | Website Linking Policy | Branding |
| `repo_policy` | Repository Policy | Infrastructure |
| `website_policy` | Website Policy | Infrastructure |
| `press` | Press & Marketing Policy | Press |
| `sponsorship` | Sponsorship Requirements | Fundraising |
| `privacy` | Privacy Policy | Privacy |
| `incubator` | Incubator Podling Policies | Incubator |
