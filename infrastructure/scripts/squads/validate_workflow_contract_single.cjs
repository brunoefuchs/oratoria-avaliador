#!/usr/bin/env node

const fs = require('fs');
const os = require('os');
const path = require('path');
const yaml = require('js-yaml');

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
const CORE_AGENTS_PATH = path.join(ROOT, '.aiox-core', 'development', 'agents');
const { applyCrossSquadContract } = require('./workflow_cross_squad_contract.cjs');

function parseArgs(argv) {
  const options = {
    file: '',
    strict: false,
    failOnWarnings: false,
    report: '',
    json: false,
    verbose: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];

    if (arg === '--file') {
      const value = argv[i + 1];
      if (!value) {
        throw new Error('missing value for --file');
      }
      options.file = value;
      i += 1;
      continue;
    }

    if (arg === '--strict') {
      options.strict = true;
      continue;
    }

    if (arg === '--fail-on-warnings') {
      options.failOnWarnings = true;
      continue;
    }

    if (arg === '--report') {
      const value = argv[i + 1];
      if (!value) {
        throw new Error('missing value for --report');
      }
      options.report = value;
      i += 1;
      continue;
    }

    if (arg === '--json') {
      options.json = true;
      continue;
    }

    if (arg === '--verbose') {
      options.verbose = true;
      continue;
    }

    throw new Error(`unknown argument: ${arg}`);
  }

  if (!options.file) {
    throw new Error('missing required argument: --file');
  }

  return options;
}

function resolveSquadAgentsPath(workflowAbsPath) {
  const rel = path.relative(ROOT, workflowAbsPath).split(path.sep);
  if (rel.length >= 4 && rel[0] === 'squads' && rel[2] === 'workflows') {
    return path.join(ROOT, 'squads', rel[1], 'agents');
  }
  return null;
}

function normalizeAgentRefs(value) {
  if (Array.isArray(value)) {
    return value.map(normalizeAgentRefs);
  }

  if (!value || typeof value !== 'object') {
    return value;
  }

  const normalized = {};
  for (const [key, child] of Object.entries(value)) {
    if (key === 'agent' && typeof child === 'string') {
      normalized[key] = child.replace(/^@+/, '');
      continue;
    }
    normalized[key] = normalizeAgentRefs(child);
  }

  return normalized;
}

function createValidatorInputCopy(workflowAbsPath) {
  const document = yaml.load(fs.readFileSync(workflowAbsPath, 'utf8'));
  const normalized = normalizeAgentRefs(document);
  const tempPath = path.join(
    os.tmpdir(),
    `workflow-validator-${path.basename(workflowAbsPath, path.extname(workflowAbsPath))}-${process.pid}-${Date.now()}.yaml`
  );
  fs.writeFileSync(tempPath, yaml.dump(normalized), 'utf8');
  return tempPath;
}

function printHumanSummary(report) {
  const status = report.status;
  console.log(`${status}: workflow contract validation (${report.workflow})`);
  console.log(` - errors: ${report.errors}`);
  console.log(` - warnings: ${report.warnings}`);
  if (report.report_path) {
    console.log(` - report: ${report.report_path}`);
  }
}

async function main() {
  let WorkflowValidator;
  try {
    ({ WorkflowValidator } = require(path.join(ROOT, '.aiox-core', 'development', 'scripts', 'workflow-validator')));
  } catch (error) {
    console.error('ERROR: failed to load WorkflowValidator');
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }

  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`ERROR: ${error.message}`);
    console.error('Usage: validate_workflow_contract_single.cjs --file <path> [--strict] [--fail-on-warnings] [--report path] [--json] [--verbose]');
    process.exit(1);
  }

  const workflowAbsPath = path.isAbsolute(options.file)
    ? options.file
    : path.join(ROOT, options.file);

  if (!fs.existsSync(workflowAbsPath)) {
    console.error(`ERROR: workflow file not found: ${options.file}`);
    process.exit(1);
  }

  const validatorInputPath = createValidatorInputCopy(workflowAbsPath);
  const validator = new WorkflowValidator({
    verbose: options.verbose,
    strict: options.strict,
    agentsPath: CORE_AGENTS_PATH,
    squadAgentsPath: resolveSquadAgentsPath(workflowAbsPath),
  });

  const baseResult = await validator.validate(validatorInputPath);
  const result = applyCrossSquadContract({
    root: ROOT,
    workflowAbsPath,
    squadAgentsPath: resolveSquadAgentsPath(workflowAbsPath),
    result: baseResult,
  });
  fs.rmSync(validatorInputPath, { force: true });
  const errors = result.errors || [];
  const warnings = result.warnings || [];
  const shouldFail = errors.length > 0 || (options.failOnWarnings && warnings.length > 0);

  const report = {
    generated_at: new Date().toISOString(),
    repo_root: ROOT,
    workflow: path.relative(ROOT, workflowAbsPath),
    options: {
      strict: options.strict,
      fail_on_warnings: options.failOnWarnings,
    },
    valid: result.valid,
    status: shouldFail ? 'FAIL' : 'PASS',
    errors: errors.length,
    warnings: warnings.length,
    errors_detail: errors,
    warnings_detail: warnings,
    cross_squad_contract: result.cross_squad_contract || null,
    report_path: null,
  };

  if (options.report) {
    const reportPath = path.isAbsolute(options.report)
      ? options.report
      : path.join(ROOT, options.report);
    fs.mkdirSync(path.dirname(reportPath), { recursive: true });
    fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf-8');
    report.report_path = path.relative(ROOT, reportPath);
  }

  if (options.json) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    printHumanSummary(report);
  }

  process.exit(shouldFail ? 1 : 0);
}

main().catch((error) => {
  console.error('ERROR: unexpected failure while validating workflow contract');
  console.error(error instanceof Error ? error.stack || error.message : String(error));
  process.exit(1);
});
