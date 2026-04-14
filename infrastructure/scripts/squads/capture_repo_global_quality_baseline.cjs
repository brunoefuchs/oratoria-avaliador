#!/usr/bin/env node

const { spawnSync } = require('child_process');

const BASELINE_COMMANDS = [
  { id: 'lint', command: 'npm run lint' },
  { id: 'typecheck', command: 'npm run typecheck' },
  { id: 'test', command: 'npm test' },
];

function trimOutput(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function classifyExecution(result) {
  if (result.error || result.timedOut || result.signal) {
    return 'inconclusive';
  }

  const combinedOutput = `${result.stderr || ''}\n${result.stdout || ''}`.toLowerCase();
  if (result.exitCode === 127 || combinedOutput.includes('command not found')) {
    return 'inconclusive';
  }

  return result.exitCode === 0 ? 'pass' : 'fail';
}

function summarizeResults(results) {
  const counts = { pass: 0, fail: 0, inconclusive: 0 };

  for (const result of results) {
    counts[result.status] += 1;
  }

  let overallStatus = 'pass';
  if (counts.inconclusive > 0) {
    overallStatus = 'inconclusive';
  } else if (counts.fail > 0) {
    overallStatus = 'fail';
  }

  return {
    overall_status: overallStatus,
    counts,
  };
}

function defaultRunCommand(command) {
  const execution = spawnSync(command, {
    shell: true,
    cwd: process.cwd(),
    encoding: 'utf8',
    maxBuffer: 10 * 1024 * 1024,
    timeout: 15 * 60 * 1000,
  });

  return {
    command,
    exitCode: typeof execution.status === 'number' ? execution.status : null,
    signal: execution.signal || null,
    timedOut: execution.error?.code === 'ETIMEDOUT',
    stdout: trimOutput(execution.stdout),
    stderr: trimOutput(execution.stderr),
    error: execution.error
      ? {
          message: execution.error.message,
          code: execution.error.code || null,
        }
      : null,
  };
}

function captureRepoGlobalQualityBaseline(runCommand = defaultRunCommand) {
  const startedAt = new Date().toISOString();
  const gates = BASELINE_COMMANDS.map(({ id, command }) => {
    const execution = runCommand(command);
    return {
      id,
      command,
      status: classifyExecution(execution),
      exit_code: execution.exitCode,
      signal: execution.signal,
      timed_out: execution.timedOut,
      stdout: execution.stdout,
      stderr: execution.stderr,
      error: execution.error,
    };
  });

  return {
    started_at: startedAt,
    completed_at: new Date().toISOString(),
    baseline_scope: 'repo-global-quality-gates',
    ...summarizeResults(gates),
    gates,
  };
}

function main() {
  const baseline = captureRepoGlobalQualityBaseline();
  process.stdout.write(`${JSON.stringify(baseline, null, 2)}\n`);
}

if (require.main === module) {
  main();
}

module.exports = {
  BASELINE_COMMANDS,
  captureRepoGlobalQualityBaseline,
  classifyExecution,
  summarizeResults,
};
