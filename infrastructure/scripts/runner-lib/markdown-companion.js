'use strict';

/**
 * markdown-companion.js — Generate companion .md summaries from JSON outputs
 * Story: STORY-118.4
 *
 * Provides audience-aware Markdown generation so downstream agents
 * can consume structured findings without parsing raw JSON/JSONL.
 */

const AUDIENCE_TEMPLATES = {
  qa:      { sections: ['findings', 'reproduction', 'metrics'] },
  po:      { sections: ['findings', 'impact', 'priority', 'risk'] },
  dev:     { sections: ['findings', 'locations', 'fixes'] },
  generic: { sections: ['findings', 'metrics', 'recommendations', 'next_agent'] },
};

/**
 * Generate a Markdown companion file from structured summary data.
 * @param {string} jsonPath - Path to the source JSON/JSONL file
 * @param {object} summary - Structured summary object
 * @param {string} [summary.title] - Document title (defaults to basename of jsonPath)
 * @param {Array<{severity: string, message: string}>} [summary.findings] - Ranked findings
 * @param {Object<string, string|number>} [summary.metrics] - Key-value metrics
 * @param {string[]} [summary.recommendations] - Actionable recommendations
 * @param {string} [summary.nextAgentContext] - Context blob for the next agent in pipeline
 * @param {string} [summary.reproduction] - How to reproduce (QA audience)
 * @param {string} [summary.impact] - User impact statement (PO audience)
 * @param {string[]} [summary.locations] - Code locations (Dev audience)
 * @param {object} [options] - Generation options
 * @param {number} [options.maxFindings=10] - Cap on rendered findings
 * @param {string} [options.audience='generic'] - Audience key from AUDIENCE_TEMPLATES
 * @returns {string} Absolute path to the generated .md file
 */
function emitMarkdownCompanion(jsonPath, summary, options = {}) {
  const fs = require('fs');
  const path = require('path');
  const { maxFindings = 10, audience = 'generic' } = options;

  const mdPath = jsonPath.replace(/\.jsonl?$/, '-summary.md');
  const template = AUDIENCE_TEMPLATES[audience] || AUDIENCE_TEMPLATES.generic;

  const sections = [];
  sections.push(`# ${summary.title || path.basename(jsonPath)} -- Summary\n`);

  // Findings (ranked by severity)
  if (template.sections.includes('findings') && summary.findings?.length) {
    sections.push('## Top Findings (ranked by severity)\n');
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
    const sorted = [...summary.findings]
      .sort((a, b) => (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99))
      .slice(0, maxFindings);
    sorted.forEach((f, i) => {
      sections.push(`${i + 1}. [${(f.severity || 'info').toUpperCase()}] ${f.message}`);
    });
    sections.push('');
  }

  // Metrics
  if (template.sections.includes('metrics') && summary.metrics) {
    sections.push('## Key Metrics\n');
    Object.entries(summary.metrics).forEach(([k, v]) => {
      sections.push(`- **${k}:** ${v}`);
    });
    sections.push('');
  }

  // Recommendations
  if (template.sections.includes('recommendations') && summary.recommendations?.length) {
    sections.push('## Actionable Recommendations\n');
    summary.recommendations.forEach((r, i) => sections.push(`${i + 1}. ${r}`));
    sections.push('');
  }

  // Reproduction steps (QA audience)
  if (template.sections.includes('reproduction') && summary.reproduction) {
    sections.push('## How to Reproduce\n');
    sections.push(summary.reproduction);
    sections.push('');
  }

  // Impact (PO audience)
  if (template.sections.includes('impact') && summary.impact) {
    sections.push('## User Impact\n');
    sections.push(summary.impact);
    sections.push('');
  }

  // Priority (PO audience)
  if (template.sections.includes('priority') && summary.priority) {
    sections.push('## Priority Assessment\n');
    sections.push(summary.priority);
    sections.push('');
  }

  // Risk (PO audience)
  if (template.sections.includes('risk') && summary.risk) {
    sections.push('## Risk Analysis\n');
    sections.push(summary.risk);
    sections.push('');
  }

  // Code locations (Dev audience)
  if (template.sections.includes('locations') && summary.locations?.length) {
    sections.push('## Code Locations\n');
    summary.locations.forEach(l => sections.push(`- \`${l}\``));
    sections.push('');
  }

  // Suggested fixes (Dev audience)
  if (template.sections.includes('fixes') && summary.fixes?.length) {
    sections.push('## Suggested Fixes\n');
    summary.fixes.forEach((f, i) => sections.push(`${i + 1}. ${f}`));
    sections.push('');
  }

  // Context for Next Agent
  if (template.sections.includes('next_agent') && summary.nextAgentContext) {
    sections.push('## Context for Next Agent\n');
    sections.push(summary.nextAgentContext);
    sections.push('');
  }

  // Footer
  sections.push('---');
  sections.push(`*Auto-generated companion for \`${path.basename(jsonPath)}\`*`);
  sections.push('');

  const content = sections.join('\n');
  fs.writeFileSync(mdPath, content, 'utf8');
  return mdPath;
}

module.exports = { emitMarkdownCompanion, AUDIENCE_TEMPLATES };
