#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const args = {
    maxDrop: 5,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    switch (arg) {
      case '--trace-file':
        args.traceFile = argv[++i];
        break;
      case '--runner-lib-dir':
        args.runnerLibDir = argv[++i];
        break;
      case '--output':
        args.output = argv[++i];
        break;
      case '--input-report':
        args.inputReport = argv[++i];
        break;
      case '--update-baseline':
        args.updateBaseline = argv[++i];
        break;
      case '--check-baseline':
        args.checkBaseline = argv[++i];
        break;
      case '--max-drop':
        args.maxDrop = Number(argv[++i]);
        break;
      default:
        throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return args;
}

function walk(dir, predicate, results = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(fullPath, predicate, results);
      continue;
    }
    if (predicate(fullPath)) {
      results.push(fullPath);
    }
  }
  return results;
}

function isTargetShellFile(fullPath, runnerLibDir) {
  const rel = path.relative(runnerLibDir, fullPath).split(path.sep);
  if (rel[0] === 'tests' || rel[0] === 'docs') {
    return false;
  }
  return fullPath.endsWith('.sh');
}

function isCoverableLine(line) {
  const trimmed = line.trim();
  return trimmed !== '' && !trimmed.startsWith('#');
}

function loadCoverableLines(filePath) {
  const lines = fs.readFileSync(filePath, 'utf8').split(/\r?\n/);
  const coverable = new Set();
  lines.forEach((line, index) => {
    if (isCoverableLine(line)) {
      coverable.add(index + 1);
    }
  });
  return coverable;
}

function parseTraceFile(traceFile, runnerLibDir) {
  const executed = new Map();
  if (!traceFile || !fs.existsSync(traceFile)) {
    return executed;
  }

  const traceLines = fs.readFileSync(traceFile, 'utf8').split(/\r?\n/);
  const pattern = /^\++(.+?\.sh):([0-9]+):/;

  for (const line of traceLines) {
    const match = line.match(pattern);
    if (!match) {
      continue;
    }

    const filePath = path.resolve(match[1]);
    if (!filePath.startsWith(path.resolve(runnerLibDir))) {
      continue;
    }
    if (!isTargetShellFile(filePath, runnerLibDir)) {
      continue;
    }

    const lineNumber = Number(match[2]);
    if (!executed.has(filePath)) {
      executed.set(filePath, new Set());
    }
    executed.get(filePath).add(lineNumber);
  }

  return executed;
}

function buildReport({ runnerLibDir, traceFile }) {
  const targetFiles = walk(
    runnerLibDir,
    (fullPath) => isTargetShellFile(fullPath, runnerLibDir),
  ).sort();
  const executedMap = parseTraceFile(traceFile, runnerLibDir);
  const testFiles = walk(
    path.join(runnerLibDir, 'tests'),
    (fullPath) => fullPath.endsWith('.sh') && !fullPath.endsWith('templates/test-runner-template.sh'),
  ).sort();

  let totalCoverableLines = 0;
  let executedCoverableLines = 0;
  const coveredModules = [];
  const uncoveredModules = [];
  const files = [];

  for (const filePath of targetFiles) {
    const relPath = path.relative(runnerLibDir, filePath).split(path.sep).join('/');
    const coverable = loadCoverableLines(filePath);
    const executedLines = executedMap.get(filePath) || new Set();
    const coveredLines = [...executedLines].filter((lineNo) => coverable.has(lineNo));

    totalCoverableLines += coverable.size;
    executedCoverableLines += coveredLines.length;

    const moduleEntry = {
      path: relPath,
      coverable_lines: coverable.size,
      executed_lines: coveredLines.length,
      coverage_pct: coverable.size === 0
        ? 0
        : Number(((coveredLines.length / coverable.size) * 100).toFixed(1)),
    };
    files.push(moduleEntry);

    if (coveredLines.length > 0) {
      coveredModules.push(relPath.replace(/\.sh$/, ''));
    } else {
      uncoveredModules.push(relPath.replace(/\.sh$/, ''));
    }
  }

  const coveragePct = totalCoverableLines === 0
    ? 0
    : Number(((executedCoverableLines / totalCoverableLines) * 100).toFixed(1));
  const moduleCoveragePct = targetFiles.length === 0
    ? 0
    : Number(((coveredModules.length / targetFiles.length) * 100).toFixed(1));

  return {
    generated_at: new Date().toISOString(),
    measurement_method: 'line-level shell coverage via bash xtrace (non-empty, non-comment lines)',
    runner_lib: {
      total_modules: targetFiles.length,
      modules_covered: coveredModules.length,
      module_coverage_pct: moduleCoveragePct,
      total_coverable_lines: totalCoverableLines,
      executed_lines: executedCoverableLines,
      coverage_pct: coveragePct,
      covered_modules: coveredModules,
      uncovered_modules: uncoveredModules,
      test_files: testFiles.length,
      files,
    },
  };
}

function ensureParentDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function writeJson(filePath, data) {
  ensureParentDir(filePath);
  fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`);
}

function localDateStamp() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Sao_Paulo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date());
}

function buildBaselineDocument(report, baselinePath) {
  const existing = fs.existsSync(baselinePath)
    ? JSON.parse(fs.readFileSync(baselinePath, 'utf8'))
    : {};

  return {
    baseline_date: localDateStamp(),
    story: 'STORY-111.7 (Epic 111)',
    measurement_method: report.measurement_method,
    runner_lib: {
      ...report.runner_lib,
      note: 'Measured from full runner-lib shell suite with bash xtrace coverage.',
    },
    governance_scripts: existing.governance_scripts || {
      total_scripts: 0,
      scripts_with_tests: 0,
      coverage_pct: 0,
      scripts: [],
      note: 'Not part of the runner-lib shell coverage threshold gate.',
    },
    overall: {
      scope: 'runner-lib',
      coverage_pct: report.runner_lib.coverage_pct,
      target_pct: 40,
      note: 'Epic 111 enforces runner-lib against this baseline with max 5 percentage point regression.',
    },
  };
}

function checkBaseline(report, baselinePath, maxDrop) {
  const baseline = JSON.parse(fs.readFileSync(baselinePath, 'utf8'));
  const baselinePct = Number(baseline?.runner_lib?.coverage_pct ?? 0);
  const currentPct = Number(report?.runner_lib?.coverage_pct ?? 0);
  const minimumAllowed = Number((baselinePct - maxDrop).toFixed(1));

  if (currentPct < minimumAllowed) {
    console.error(
      `Runner-lib coverage regression: current ${currentPct}% is below allowed floor ${minimumAllowed}% (baseline ${baselinePct}%, max drop ${maxDrop}pts).`,
    );
    process.exit(1);
  }

  console.log(
    `Runner-lib coverage OK: current ${currentPct}% vs baseline ${baselinePct}% (max drop ${maxDrop}pts, floor ${minimumAllowed}%).`,
  );
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  let report;

  if (args.inputReport) {
    report = JSON.parse(fs.readFileSync(args.inputReport, 'utf8'));
  } else {
    if (!args.traceFile || !args.runnerLibDir) {
      throw new Error('Generation mode requires --trace-file and --runner-lib-dir.');
    }
    report = buildReport({
      runnerLibDir: path.resolve(args.runnerLibDir),
      traceFile: path.resolve(args.traceFile),
    });
  }

  if (args.output) {
    writeJson(path.resolve(args.output), report);
  }

  if (args.updateBaseline) {
    const baseline = buildBaselineDocument(report, path.resolve(args.updateBaseline));
    writeJson(path.resolve(args.updateBaseline), baseline);
  }

  if (args.checkBaseline) {
    checkBaseline(report, path.resolve(args.checkBaseline), args.maxDrop);
  }

  if (!args.output && !args.updateBaseline && !args.checkBaseline) {
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  }
}

main();
