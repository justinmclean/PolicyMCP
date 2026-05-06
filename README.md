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

## First-time setup

After installing, warm the cache by running the `refresh_cache` tool once (e.g. ask Claude to "refresh all policies"). This fetches all ~55 policy documents and caches them locally for 30 days — without it, searches will skip any policies not yet cached.

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
- Can a company call its commercial product "Apache Foo Enterprise Edition"?
- Can a third party use "Apache Foo" in the name of their commercial product?
- What must appear on a project website for trademark compliance?

**Infrastructure, press, privacy, and reporting**
- Can a project use an external Git host like GitLab as its primary code repository?
- Can a project host its website on GitHub Pages?
- Can a company issue a press release announcing new features they've added support for in an Apache project?
- Are Apache mailing list archives public, and what does that mean for personal data posted to them?
- If a PMC discovers a company misusing their project's trademark, who handles it and what should they do first?
- Can a project list corporate affiliations next to committer names on a "Who We Are" page?
- What fields are required in every PMC board report?

**Apache Foo scenarios**
- Apache Foo wants to publish container images, nightly builds, and release candidates from the same Docker Hub namespace. Which parts are allowed, and what labels or warnings are needed?
- ExampleCo donated most of Apache Foo's original code and still employs most committers. What website, branding, and project independence issues should the PMC watch for?
- A security researcher privately reports a vulnerability in Apache Foo, but a downstream vendor wants to publish a fix immediately. How should the PMC coordinate disclosure, release voting, and public communication?
- Apache Foo wants to accept a large generated code contribution produced with AI tooling and containing third-party snippets. Which licensing, provenance, and source-header checks apply?
- The Apache Foo PMC wants to run an in-person "FooCon" with paid sponsors, project swag, and talks by vendors. Which event branding, merchandise, press, and conduct policies apply?
- A former Apache Foo committer asks for their name and email to be removed from old mailing list archives and Git commits. What do the privacy, public archive, and repository policies imply?
- Apache Foo has not released in two years, has no recent PMC additions, and depends on infrastructure that Infra wants to retire. What should the next board report include?

## Policy documents

| Key | Title | Section |
|---|---|---|
| `pmc` | PMC Guide | Community And Project Oversight |
| `code_of_conduct` | Code of Conduct | Community And Project Oversight |
| `anti_harassment` | Anti-Harassment Policy | Community And Project Oversight |
| `public_archives` | Public Forum Archive Policy | Community And Project Oversight |
| `project_independence` | Project Independence | Independence |
| `board_reporting` | Board Reporting Requirements | Reporting |
| `release_policy` | Release Policy | Release |
| `voting` | Apache Voting Process | Release |
| `release_distribution` | Release Distribution Policy | Release |
| `docker_hub` | Docker Hub Policy | Release |
| `release_download_pages` | Release Download Pages Policy | Release |
| `nightlies` | Project Use of nightlies.apache.org | Release |
| `security` | Security Team Guidance | Security |
| `security_committers` | Vulnerability Handling for Committers | Security |
| `licenses` | Contributor License Agreements | Licensing |
| `apply_license` | Applying the Apache License, Version 2.0 | Licensing |
| `cla_faq` | CLA FAQ | Licensing |
| `source_headers` | Apache Source Headers | Licensing |
| `resolved_licenses` | Approved/Resolved Third-Party Licenses | Licensing |
| `crypto_policy` | Handling Cryptography within an ASF Release | Licensing |
| `generative_tooling` | Generative Tooling Guidance | Licensing |
| `branding` | Project Branding Requirements | Branding |
| `trademark_maintenance` | Trademark Maintenance Responsibilities | Branding |
| `website_linking` | Website Linking Policy | Branding |
| `event_branding` | Third-Party Event Branding Policy | Branding |
| `merchandise_branding` | Non-Software Merchandise Branding Policy | Branding |
| `domain_name_branding` | Domain Name Branding Policy | Branding |
| `downstream_distribution` | Apache Software Downstream Distribution Policy | Branding |
| `podling_branding` | Incubator Podling Branding Guide | Branding |
| `event_code_of_conduct` | Event Code of Conduct | Events |
| `trademark_policy` | ASF Trademark Policy | Branding |
| `repo_policy` | Repository Policy | Infrastructure |
| `infra_site_ban` | Site-Wide Ban | Infrastructure |
| `committer_outreach` | Outreach to Committers | Infrastructure |
| `content_moderation` | Content Moderation | Infrastructure |
| `mail_rejection` | Mail Rejection Policy | Infrastructure |
| `spam_reporting` | Dealing with Spam in Your ASF Email Account | Infrastructure |
| `password_policy` | Password Requirements | Infrastructure |
| `third_party_services` | Policy on Issues in Third-Party Services | Infrastructure |
| `slack_policy` | Policy for Using ASF Slack | Infrastructure |
| `sensitive_information` | Policy on Sharing Sensitive Information with Infra | Infrastructure |
| `github_actions` | GitHub Actions | Infrastructure |
| `website_policy` | Website Policy | Infrastructure |
| `content_security_policy` | Content Security Policy | Infrastructure |
| `app_upgrade_policy` | Application Upgrades | Infrastructure |
| `backup_policy` | Backups | Infrastructure |
| `os_upgrade_policy` | Operating System Upgrades | Infrastructure |
| `vm_policy` | Virtual Machines for Projects | Infrastructure |
| `jira_account_approval` | Approving Jira Account Requests | Infrastructure |
| `jira_account_retention` | Jira Account Retention Policy | Infrastructure |
| `press` | Press & Marketing Policy | Press |
| `sponsorship` | Sponsorship Requirements | Fundraising |
| `privacy` | Privacy Policy | Privacy |
| `privacy_contributors` | Privacy Policy for Contributors | Privacy |
| `privacy_committers` | Privacy Policy for Committers | Privacy |
| `privacy_project_websites` | Privacy Policy for Project Websites | Privacy |
| `privacy_downloadable_products_high` | Privacy Policy for ASF Downloadable Applications (High Privacy Standards) | Privacy |
| `privacy_downloadable_products_medium` | Privacy Policy for Products with Medium Privacy Standards | Privacy |
| `privacy_mailing_lists` | Mailing List Policy | Privacy |
| `incubator` | Incubator Podling Policies | Incubator |
| `incubator_ip_clearance` | Incubator IP Clearance | Incubator |
