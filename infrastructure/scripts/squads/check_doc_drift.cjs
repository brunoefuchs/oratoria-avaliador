#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

function findRepoRoot(startDir) {
  let current = path.resolve(startDir);

  while (true) {
    if (
      fs.existsSync(path.join(current, 'package.json')) &&
      fs.existsSync(path.join(current, '.aiox-core'))
    ) {
      return current;
    }

    const parent = path.dirname(current);
    if (parent === current) {
      throw new Error(`failed to resolve repository root from ${startDir}`);
    }
    current = parent;
  }
}

const ROOT = findRepoRoot(__dirname);

function parseArgs(argv) {
  const options = {
    squad: null,
    json: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--squad') {
      const value = argv[i + 1];
      if (!value) {
        throw new Error('missing value for --squad');
      }
      options.squad = value;
      i += 1;
      continue;
    }
    if (arg === '--json') {
      options.json = true;
      continue;
    }
    throw new Error(`unknown argument: ${arg}`);
  }

  if (!options.squad) {
    throw new Error('missing required argument: --squad');
  }

  return options;
}

function exists(root, relativePath) {
  return fs.existsSync(path.join(root, relativePath));
}

function listFiles(root, relativeDir, extensions) {
  const absoluteDir = path.join(root, relativeDir);
  if (!fs.existsSync(absoluteDir)) {
    return [];
  }

  return fs
    .readdirSync(absoluteDir)
    .filter((file) => extensions.some((ext) => file.endsWith(ext)))
    .sort((a, b) => a.localeCompare(b));
}

function readFile(root, relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function detectBridgeAgents(squad, root = ROOT) {
  const agentsDir = path.join('squads', squad, 'agents');
  return listFiles(root, agentsDir, ['.md'])
    .filter((fileName) => {
      const content = readFile(root, path.join(agentsDir, fileName));
      return (
        content.includes('ACTIVATION-NOTICE: This file is a cross-squad bridge') ||
        content.includes('Cross-squad runtime bridge') ||
        content.includes('cross-squad bridge')
      );
    })
    .map((fileName) => path.basename(fileName, '.md'));
}

function collectCounts(squad, root = ROOT) {
  const totalAgents = listFiles(root, path.join('squads', squad, 'agents'), ['.md']).length;
  const bridgeAgents = detectBridgeAgents(squad, root);
  return {
    local_agents: totalAgents - bridgeAgents.length,
    total_agents: totalAgents,
    bridges: bridgeAgents.length,
    tasks: listFiles(root, path.join('squads', squad, 'tasks'), ['.md']).length,
    workflows: listFiles(root, path.join('squads', squad, 'workflows'), ['.yaml', '.yml']).length,
    checklists: listFiles(root, path.join('squads', squad, 'checklists'), ['.md']).length,
    templates: listFiles(root, path.join('squads', squad, 'templates'), ['.md', '.yaml', '.yml']).length,
  };
}

function extractNumberMentions(content, patterns) {
  const values = [];
  for (const pattern of patterns) {
    for (const match of content.matchAll(pattern)) {
      values.push(Number(match[1]));
    }
  }
  return values.filter((value) => Number.isFinite(value));
}

function checkCountMentions(relativePath, content, counts) {
  const findings = [];
  const countChecks = [
    {
      id: 'local_agents',
      actual: counts.local_agents,
      patterns: [/\b(\d+)\s+local agents?\b/gi],
      message: 'local agent count drift',
    },
    {
      id: 'bridges',
      actual: counts.bridges,
      patterns: [/\b(\d+)\s+cross-squad bridges?\b/gi, /\b(\d+)\s+bridges?\b/gi],
      message: 'bridge count drift',
    },
    {
      id: 'total_agents',
      actual: counts.total_agents,
      patterns: [/\b(\d+)\s+agents?\b/gi],
      message: 'agent count drift',
    },
    {
      id: 'tasks',
      actual: counts.tasks,
      patterns: [/\b(\d+)\s+tasks?\b/gi],
      message: 'task count drift',
    },
    {
      id: 'workflows',
      actual: counts.workflows,
      patterns: [/\b(\d+)\s+workflows?\b/gi],
      message: 'workflow count drift',
    },
    {
      id: 'checklists',
      actual: counts.checklists,
      patterns: [/\b(\d+)\s+checklists?\b/gi],
      message: 'checklist count drift',
    },
    {
      id: 'templates',
      actual: counts.templates,
      patterns: [/\b(\d+)\s+templates?\b/gi],
      message: 'template count drift',
    },
  ];

  for (const check of countChecks) {
    const mentions = extractNumberMentions(content, check.patterns);
    if (mentions.length === 0) {
      continue;
    }
    if (!mentions.includes(check.actual)) {
      findings.push({
        code: 'DOC_COUNT_MISMATCH',
        file: relativePath,
        subject: check.id,
        actual: check.actual,
        mentioned: mentions,
        message: `${check.message}: expected ${check.actual}, found mentions ${mentions.join(', ')}`,
      });
    }
  }

  return findings;
}

function checkBridgeMentions(relativePath, content, bridgeAgents) {
  if (bridgeAgents.length === 0) {
    return [];
  }

  const findings = [];
  const mentionsCrossSquad = content.includes('cross-squad bridge') || content.includes('cross-squad:');

  for (const bridgeAgent of bridgeAgents) {
    if (!content.includes(bridgeAgent) && !mentionsCrossSquad) {
      findings.push({
        code: 'DOC_BRIDGE_UNDECLARED',
        file: relativePath,
        subject: bridgeAgent,
        message: `bridge agent "${bridgeAgent}" is not declared in ${relativePath}`,
      });
    }
  }

  return findings;
}

function buildReport(squad, options = {}) {
  const root = options.root || ROOT;
  const squadDir = path.join(root, 'squads', squad);
  if (!fs.existsSync(squadDir)) {
    return {
      generated_at: new Date().toISOString(),
      squad,
      status: 'FAIL',
      counts: null,
      bridge_agents: [],
      files_checked: [],
      findings: [
        {
          code: 'DOC_SQUAD_NOT_FOUND',
          file: `squads/${squad}`,
          message: `squad "${squad}" does not exist`,
        },
      ],
    };
  }

  const counts = collectCounts(squad, root);
  const bridgeAgents = detectBridgeAgents(squad, root);
  const docFiles = [
    path.join('squads', squad, 'README.md'),
    path.join('squads', squad, 'ARCHITECTURE.md'),
    path.join('squads', squad, 'CHANGELOG.md'),
  ].filter((relativePath) => exists(root, relativePath));

  if (docFiles.length === 0) {
    return {
      generated_at: new Date().toISOString(),
      squad,
      status: 'FAIL',
      counts,
      bridge_agents: bridgeAgents,
      files_checked: [],
      findings: [
        {
          code: 'DOC_REFERENCE_FILES_MISSING',
          file: `squads/${squad}`,
          message: 'no README.md, ARCHITECTURE.md, or CHANGELOG.md found for doc drift validation',
        },
      ],
    };
  }

  const findings = [];

  for (const relativePath of docFiles) {
    const content = readFile(root, relativePath);
    if (relativePath.endsWith('README.md') || relativePath.endsWith('ARCHITECTURE.md')) {
      findings.push(...checkCountMentions(relativePath, content, counts));
    }
    findings.push(...checkBridgeMentions(relativePath, content, bridgeAgents));
  }

  return {
    generated_at: new Date().toISOString(),
    squad,
    status: findings.length === 0 ? 'PASS' : 'FAIL',
    counts,
    bridge_agents: bridgeAgents,
    files_checked: docFiles,
    findings,
  };
}

function printHuman(report) {
  console.log(`${report.status}: doc drift check (${report.squad})`);
  console.log(` - files_checked: ${report.files_checked.length}`);
  console.log(` - bridge_agents: ${report.bridge_agents.length}`);
  console.log(` - findings: ${report.findings.length}`);
  if (report.findings.length > 0) {
    for (const finding of report.findings) {
      console.log(` - [${finding.code}] ${finding.file}: ${finding.message}`);
    }
  }
}

function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`ERROR: ${error.message}`);
    console.error('Usage: check_doc_drift.cjs --squad <name> [--json]');
    process.exit(1);
  }

  const report = buildReport(options.squad);
  if (options.json) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    printHuman(report);
  }

  process.exit(report.status === 'PASS' ? 0 : 1);
}

if (require.main === module) {
  main();
}

module.exports = {
  buildReport,
  checkBridgeMentions,
  checkCountMentions,
  detectBridgeAgents,
};
