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

const TARGET_DIRS = [
  'squads/squad-creator',
  'squads/squad-creator-pro',
];

const FORBIDDEN_FILENAMES = new Set([
  '.state.json',
  '.validate-state.json',
  '.active-squad',
]);

const FORBIDDEN_SUFFIXES = [
  'metadata/state.json',
];

const SOURCE_SCAN_DIRS = [
  'squads/squad-creator/scripts',
  'squads/squad-creator/tasks',
  'squads/squad-creator/config',
  'squads/squad-creator/checklists',
  'squads/squad-creator/agents',
  'squads/squad-creator/workflows',
  'squads/squad-creator-pro/scripts',
  'squads/squad-creator-pro/tasks',
  'squads/squad-creator-pro/config',
  'squads/squad-creator-pro/checklists',
  'squads/squad-creator-pro/agents',
  'squads/squad-creator-pro/workflows',
];

const IGNORE_DIRS = new Set(['__pycache__', 'node_modules', '.git']);
const IGNORE_FILE_SUFFIXES = ['.pyc', '.pyo'];

const FORBIDDEN_PATH_TOKENS = [
  'squads/squad-creator-pro/.state.json',
  'squads/.active-squad',
  '.validate-state.json',
  'metadata/state.json',
  'outputs/squad-creator/ecosystem-registry.yaml',
  'outputs/minds/',
  'outputs/squad_creation/',
  'outputs/squad_upgrade/',
  'outputs/discovery/',
  'outputs/research/',
];

function parseArgs(argv) {
  const options = {
    fixture: '',
    json: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];

    if (arg === '--fixture') {
      const value = argv[i + 1];
      if (!value) {
        throw new Error('missing value for --fixture');
      }
      options.fixture = value;
      i += 1;
      continue;
    }

    if (arg === '--json') {
      options.json = true;
      continue;
    }

    throw new Error(`unknown argument: ${arg}`);
  }

  return options;
}

function toPosix(p) {
  return p.split(path.sep).join('/');
}

function walkFiles(baseDir, out) {
  if (!fs.existsSync(baseDir)) return;
  const entries = fs.readdirSync(baseDir, { withFileTypes: true });

  for (const entry of entries) {
    if (IGNORE_DIRS.has(entry.name)) {
      continue;
    }

    const fullPath = path.join(baseDir, entry.name);
    if (entry.isDirectory()) {
      walkFiles(fullPath, out);
      continue;
    }

    if (IGNORE_FILE_SUFFIXES.some((suffix) => entry.name.endsWith(suffix))) {
      continue;
    }

    out.push(fullPath);
  }
}

function checkForbiddenArtifacts(root = ROOT) {
  const violations = [];

  for (const relDir of TARGET_DIRS) {
    const absDir = path.join(root, relDir);
    const files = [];
    walkFiles(absDir, files);

    for (const absFile of files) {
      const relFile = toPosix(path.relative(root, absFile));
      const base = path.basename(absFile);

      if (FORBIDDEN_FILENAMES.has(base)) {
        violations.push({ type: 'forbidden_file', path: relFile });
        continue;
      }

      const normalized = toPosix(absFile);
      for (const suffix of FORBIDDEN_SUFFIXES) {
        if (normalized.endsWith(`/${suffix}`)) {
          violations.push({ type: 'forbidden_suffix', path: relFile, suffix });
          break;
        }
      }
    }
  }

  return violations;
}

function checkForbiddenReferences(root = ROOT) {
  const violations = [];

  for (const relDir of SOURCE_SCAN_DIRS) {
    const absDir = path.join(root, relDir);
    const files = [];
    walkFiles(absDir, files);

    for (const absFile of files) {
      let content = '';
      try {
        content = fs.readFileSync(absFile, 'utf8');
      } catch {
        continue;
      }

      for (const token of FORBIDDEN_PATH_TOKENS) {
        if (content.includes(token)) {
          violations.push({
            type: 'forbidden_reference',
            path: toPosix(path.relative(root, absFile)),
            token,
          });
        }
      }
    }
  }

  return violations;
}

function buildReport({
  artifactViolations,
  referenceViolations,
  source = 'repo-scan',
  fixture = null,
} = {}) {
  const violations = [...artifactViolations, ...referenceViolations];

  return {
    generated_at: new Date().toISOString(),
    repo_root: ROOT,
    source,
    fixture,
    status: violations.length === 0 ? 'PASS' : 'FAIL',
    artifact_violations: artifactViolations,
    reference_violations: referenceViolations,
    violations,
    summary: {
      artifacts: artifactViolations.length,
      references: referenceViolations.length,
      total: violations.length,
    },
  };
}

function printHuman(report) {
  console.log(`${report.status}: squad runtime SSOT`);
  console.log(` - source: ${report.source}`);
  console.log(` - violations: ${report.summary.total}`);

  for (const violation of report.violations) {
    if (violation.type === 'forbidden_reference') {
      console.log(` - [${violation.type}] ${violation.path} -> ${violation.token}`);
      continue;
    }
    console.log(` - [${violation.type}] ${violation.path}`);
  }
}

function loadFixtureReport(fixturePath) {
  const absolutePath = path.isAbsolute(fixturePath)
    ? fixturePath
    : path.join(ROOT, fixturePath);

  if (!fs.existsSync(absolutePath)) {
    throw new Error(`fixture not found: ${fixturePath}`);
  }

  const raw = JSON.parse(fs.readFileSync(absolutePath, 'utf8'));
  return buildReport({
    artifactViolations: Array.isArray(raw.artifact_violations) ? raw.artifact_violations : [],
    referenceViolations: Array.isArray(raw.reference_violations) ? raw.reference_violations : [],
    source: 'fixture',
    fixture: toPosix(path.relative(ROOT, absolutePath)),
  });
}

function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`ERROR: ${error.message}`);
    console.error('Usage: validate_squad_runtime_ssot.cjs [--fixture <path>] [--json]');
    process.exit(1);
  }

  const report = options.fixture
    ? loadFixtureReport(options.fixture)
    : buildReport({
        artifactViolations: checkForbiddenArtifacts(),
        referenceViolations: checkForbiddenReferences(),
      });

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
  ROOT,
  buildReport,
  checkForbiddenArtifacts,
  checkForbiddenReferences,
  loadFixtureReport,
  parseArgs,
  toPosix,
};
