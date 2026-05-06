"""Registry of ASF policy documents."""

from __future__ import annotations

POLICY_SOURCES: dict[str, dict[str, str]] = {
    "pmc": {
        "title": "PMC Guide (Mailing Lists, Committers, PMC Members)",
        "url": "https://www.apache.org/dev/pmc.html",
        "section": "Community And Project Oversight",
        "description": "Rules for mailing lists, adding committers, and managing PMC membership",
    },
    "project_independence": {
        "title": "Project Independence",
        "url": "https://community.apache.org/projectIndependence.html",
        "section": "Independence",
        "description": "Guidelines for operating independently and for the public good",
    },
    "board_reporting": {
        "title": "Board Reporting Requirements",
        "url": "https://www.apache.org/foundation/board/reporting",
        "section": "Reporting",
        "description": "Quarterly board status report requirements for PMCs",
    },
    "release_policy": {
        "title": "Release Policy",
        "url": "https://www.apache.org/legal/release-policy",
        "section": "Release",
        "description": "Apache software release policy - what constitutes a valid release",
    },
    "voting": {
        "title": "Apache Voting Process",
        "url": "https://www.apache.org/foundation/voting.html",
        "section": "Release",
        "description": "Apache voting process for releases and other decisions",
    },
    "release_distribution": {
        "title": "Release Distribution Policy",
        "url": "https://www.apache.org/dev/release-distribution",
        "section": "Release",
        "description": "Policy for how and where Apache releases are distributed",
    },
    "security": {
        "title": "Security Team Guidance",
        "url": "https://www.apache.org/security/",
        "section": "Security",
        "description": "Security notification and disclosure procedures",
    },
    "security_committers": {
        "title": "Vulnerability Handling for Committers",
        "url": "https://www.apache.org/security/committers.html",
        "section": "Security",
        "description": "How committers should handle reported security vulnerabilities",
    },
    "licenses": {
        "title": "Contributor License Agreements (CLAs)",
        "url": "https://www.apache.org/licenses/",
        "section": "Licensing",
        "description": "CLA requirements and Apache license versions",
    },
    "source_headers": {
        "title": "Apache Source Headers",
        "url": "https://www.apache.org/legal/src-headers.html",
        "section": "Licensing",
        "description": "Required Apache license headers in source files",
    },
    "resolved_licenses": {
        "title": "Approved/Resolved Third-Party Licenses",
        "url": "https://www.apache.org/legal/resolved.html",
        "section": "Licensing",
        "description": "Which third-party licenses are Category A (allowed), B (limited), or X (forbidden)",
    },
    "branding": {
        "title": "Project Branding Requirements",
        "url": "https://www.apache.org/foundation/marks/pmcs",
        "section": "Branding",
        "description": "Trademark and branding requirements for PMC projects",
    },
    "trademark_maintenance": {
        "title": "Trademark Maintenance Responsibilities",
        "url": "https://www.apache.org/foundation/marks/responsibility.html",
        "section": "Branding",
        "description": "PMC responsibilities for maintaining Apache trademarks",
    },
    "website_linking": {
        "title": "Website Linking Policy",
        "url": "https://www.apache.org/foundation/marks/linking",
        "section": "Branding",
        "description": "Policy on linking to and from Apache project websites",
    },
    "repo_policy": {
        "title": "Repository Policy",
        "url": "https://infra.apache.org/project-repo-policy.html",
        "section": "Infrastructure",
        "description": "Policy for project source code repositories",
    },
    "website_policy": {
        "title": "Website Policy",
        "url": "https://infra.apache.org/project-site-policy.html",
        "section": "Infrastructure",
        "description": "Policy for project websites and hosting",
    },
    "press": {
        "title": "Press & Marketing Policy",
        "url": "https://www.apache.org/press/",
        "section": "Press",
        "description": "Guidelines for press releases and marketing coordination",
    },
    "sponsorship": {
        "title": "Sponsorship Requirements",
        "url": "https://www.apache.org/foundation/sponsorship.html",
        "section": "Fundraising",
        "description": "Fundraising and sponsorship policies",
    },
    "privacy": {
        "title": "Privacy Policy",
        "url": "https://privacy.apache.org/policies/privacy-policy-public.html",
        "section": "Privacy",
        "description": "ASF privacy policy",
    },
    "incubator": {
        "title": "Incubator Podling Policies",
        "url": "https://incubator.apache.org/policy/incubation.html",
        "section": "Incubator",
        "description": "Policies governing Apache Incubator podlings",
    },
}
