/**
 * RUNNER-LIB — Git Context Injection (Node.js)
 * ═══════════════════════════════════════════════════════════════
 * Generates recent git history (diffs + log) for a file, formatted
 * as Markdown context suitable for injection into agent prompts.
 *
 * Usage:
 *   const { generateGitContext } = require('./git-context');
 *   const ctx = await generateGitContext('path/to/file.js');
 *   console.log(ctx.formatted);
 *
 * Budget allocation:
 *   - 62% for diff (higher signal — shows what changed)
 *   - 38% for log  (shows commit history / trajectory)
 *
 * Story: STORY-118.1 (Code-as-Feedback: Git History Context)
 */

'use strict';

const { execFile } = require('child_process');
const path = require('path');

// ── Defaults ──
const DEFAULTS = {
  maxCommits: 20,
  diffDepth: 5,
  timeout: 2000,
  maxBytes: 8192,
};

/**
 * Run a git command with timeout, returning stdout or empty string on failure.
 * @param {string[]} args - git subcommand + arguments
 * @param {number} timeout - ms
 * @param {string} [cwd] - working directory
 * @returns {Promise<string>}
 */
function gitExec(args, timeout, cwd) {
  return new Promise((resolve) => {
    const opts = { timeout, maxBuffer: 1024 * 1024 };
    if (cwd) opts.cwd = cwd;

    execFile('git', args, opts, (err, stdout) => {
      if (err) {
        resolve('');
        return;
      }
      resolve((stdout || '').toString());
    });
  });
}

/**
 * Determine safe diff depth for the repo (handles shallow clones).
 * @param {number} requested
 * @param {number} timeout
 * @param {string} [cwd]
 * @returns {Promise<number>}
 */
async function safeDepth(requested, timeout, cwd) {
  const raw = await gitExec(['rev-list', '--count', 'HEAD'], timeout, cwd);
  const total = parseInt(raw.trim(), 10);
  if (isNaN(total) || total <= 0) return 0;
  return Math.min(total, requested);
}

/**
 * Truncate a string to a byte budget.
 * @param {string} text
 * @param {number} maxBytes
 * @returns {string}
 */
function truncateToBytes(text, maxBytes) {
  if (!text) return '';
  const buf = Buffer.from(text, 'utf8');
  if (buf.length <= maxBytes) return text;
  const truncated = buf.slice(0, maxBytes).toString('utf8');
  return truncated + '\n[...truncated to ' + maxBytes + ' bytes]';
}

/**
 * Count additions and deletions from diff text.
 * @param {string} diff
 * @returns {string} e.g. "12+/3-"
 */
function countChanges(diff) {
  if (!diff) return '0+/0-';
  const lines = diff.split('\n');
  let adds = 0;
  let dels = 0;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.length > 1 && line[0] === '+' && line[1] !== '+') adds++;
    if (line.length > 1 && line[0] === '-' && line[1] !== '-') dels++;
  }
  return adds + '+/' + dels + '-';
}

/**
 * Count non-empty lines.
 * @param {string} text
 * @returns {number}
 */
function countLines(text) {
  if (!text || !text.trim()) return 0;
  return text.trim().split('\n').length;
}

/**
 * Generate git context for a file.
 *
 * @param {string} filePath - Path to the file (relative or absolute)
 * @param {Object} [options]
 * @param {number} [options.maxCommits=20] - Max log entries
 * @param {number} [options.diffDepth=5] - How many commits back for diff
 * @param {number} [options.timeout=2000] - Timeout per git command in ms
 * @param {number} [options.maxBytes=8192] - Total output byte budget
 * @returns {Promise<{log: string, diff: string, formatted: string, summary: string}>}
 */
async function generateGitContext(filePath, options) {
  const empty = { log: '', diff: '', formatted: '', summary: '' };

  if (!filePath) return empty;

  const opts = Object.assign({}, DEFAULTS, options || {});
  const cwd = process.cwd();

  // Guard: not in a git repo
  const repoCheck = await gitExec(
    ['rev-parse', '--is-inside-work-tree'],
    opts.timeout,
    cwd
  );
  if (repoCheck.trim() !== 'true') return empty;

  // Guard: file has no history
  const historyCheck = await gitExec(
    ['log', '--oneline', '-1', '--', filePath],
    opts.timeout,
    cwd
  );
  if (!historyCheck.trim()) return empty;

  // Determine safe depth
  const depth = await safeDepth(opts.diffDepth, opts.timeout, cwd);

  // Budget: 62% diff, 38% log
  const diffBudget = Math.floor((opts.maxBytes * 62) / 100);
  const logBudget = Math.floor((opts.maxBytes * 38) / 100);

  // Fetch diff FIRST (higher signal)
  let rawDiff = '';
  if (depth > 0) {
    rawDiff = await gitExec(
      ['diff', 'HEAD~' + depth, '--', filePath],
      opts.timeout,
      cwd
    );
  }
  const diff = truncateToBytes(rawDiff, diffBudget);

  // Fetch log SECOND
  const rawLog = await gitExec(
    ['log', '--oneline', '-' + opts.maxCommits, '--', filePath],
    opts.timeout,
    cwd
  );
  const log = truncateToBytes(rawLog, logBudget);

  // Build summary
  const changeStats = countChanges(rawDiff);
  const commitCount = countLines(rawLog);
  const summary =
    'Git context for ' +
    filePath +
    ': ' +
    commitCount +
    ' commits, ' +
    changeStats +
    ' in last ' +
    depth +
    ' commits';

  // Format as Markdown
  let formatted = '### Git Context: ' + filePath + '\n' + summary + '\n';

  if (diff) {
    formatted +=
      '\n#### Recent Diff (last ' +
      depth +
      ' commits)\n```diff\n' +
      diff +
      '\n```\n';
  }

  if (log) {
    formatted +=
      '\n#### Commit Log (last ' +
      commitCount +
      ' commits)\n```\n' +
      log +
      '\n```\n';
  }

  // Final byte check
  formatted = truncateToBytes(formatted, opts.maxBytes);

  return { log: log, diff: diff, formatted: formatted, summary: summary };
}

module.exports = { generateGitContext };
