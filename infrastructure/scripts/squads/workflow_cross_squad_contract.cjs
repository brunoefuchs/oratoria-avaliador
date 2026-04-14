#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

function readYaml(filePath) {
  return yaml.load(fs.readFileSync(filePath, 'utf8')) || {};
}

function uniq(items) {
  return [...new Set(items.filter(Boolean))];
}

function normalizeWorkflowDocument(document) {
  return document?.workflow && typeof document.workflow === 'object' ? document.workflow : document || {};
}

function resolveLocalSquadName(root, workflowAbsPath) {
  const relativeParts = path.relative(root, workflowAbsPath).split(path.sep);
  if (relativeParts.length >= 4 && relativeParts[0] === 'squads' && relativeParts[2] === 'workflows') {
    return relativeParts[1];
  }
  return null;
}

function collectCrossSquadAgents(document) {
  const workflow = normalizeWorkflowDocument(document);
  const candidates = uniq([
    document && typeof document === 'object' ? document : null,
    workflow && typeof workflow === 'object' ? workflow : null,
  ]);
  const collected = new Map();

  function register(agent, squad, source) {
    if (!agent || !squad) {
      return;
    }
    const key = `${squad}::${agent}`;
    const current = collected.get(key) || {
      agent,
      owning_squad: squad,
      evidence_sources: [],
    };
    current.evidence_sources = uniq([...current.evidence_sources, source]);
    collected.set(key, current);
  }

  for (const candidate of candidates) {
    const configCrossSquad = Array.isArray(candidate?.config?.cross_squad) ? candidate.config.cross_squad : [];
    for (const item of configCrossSquad) {
      register(item?.agent || null, item?.squad || null, 'config.cross_squad');
    }

    const phases = Array.isArray(candidate?.phases) ? candidate.phases : [];
    for (const phase of phases) {
      if (typeof phase?.cross_squad === 'string') {
        register(phase.executor || phase.agent || null, phase.cross_squad, `phases.${phase.id || phase.name || 'unknown'}`);
      }
    }

    const sequence = Array.isArray(candidate?.sequence) ? candidate.sequence : [];
    for (const step of sequence) {
      if (typeof step?.cross_squad === 'string') {
        register(step.agent || null, step.cross_squad, `sequence.${step.id || step.step || 'unknown'}`);
      }
    }
  }

  return [...collected.values()];
}

function validateBridgeContent(content, { agentName, owningSquad, consumingSquad }) {
  const requiredSnippets = [
    'ACTIVATION-NOTICE:',
    'activation-instructions:',
    `Canonical agent: \`squads/${owningSquad}/agents/${agentName}.md\``,
    `Owning squad: \`${owningSquad}\``,
  ];

  if (consumingSquad) {
    requiredSnippets.push(`Consuming squad: \`${consumingSquad}\``);
  }

  const missing = requiredSnippets.filter((snippet) => !content.includes(snippet));
  return {
    valid: missing.length === 0,
    missing,
  };
}

function warningMatchesAgent(message, agentName) {
  return typeof message === 'string' && message.includes(`Agent "${agentName}"`);
}

function applyCrossSquadContract({ root, workflowAbsPath, squadAgentsPath, result }) {
  const document = readYaml(workflowAbsPath);
  const crossSquadAgents = collectCrossSquadAgents(document);

  if (crossSquadAgents.length === 0) {
    return {
      ...result,
      cross_squad_contract: {
        checked_agents: 0,
        resolved_agents: [],
        errors: [],
      },
    };
  }

  const localSquad = resolveLocalSquadName(root, workflowAbsPath);
  const suppressWarningsForAgents = new Set();
  const contractErrors = [];
  const resolvedAgents = [];

  for (const entry of crossSquadAgents) {
    const canonicalRelativePath = path.join('squads', entry.owning_squad, 'agents', `${entry.agent}.md`);
    const canonicalAbsPath = path.join(root, canonicalRelativePath);
    const localBridgeAbsPath = squadAgentsPath ? path.join(squadAgentsPath, `${entry.agent}.md`) : null;
    const localBridgeRelativePath = localBridgeAbsPath ? path.relative(root, localBridgeAbsPath) : null;
    const canonicalExists = fs.existsSync(canonicalAbsPath);
    const localBridgeExists = Boolean(localBridgeAbsPath && fs.existsSync(localBridgeAbsPath));

    if (!canonicalExists) {
      contractErrors.push({
        code: 'WF_CROSS_SQUAD_AGENT_NOT_FOUND',
        message: `Cross-squad agent "${entry.agent}" declares owning squad "${entry.owning_squad}" but canonical file is missing`,
        suggestion: `Create ${canonicalRelativePath} or fix the cross_squad declaration`,
        file: path.basename(workflowAbsPath),
      });
      continue;
    }

    suppressWarningsForAgents.add(entry.agent);

    if (localBridgeExists) {
      const bridgeContent = fs.readFileSync(localBridgeAbsPath, 'utf8');
      const bridgeValidation = validateBridgeContent(bridgeContent, {
        agentName: entry.agent,
        owningSquad: entry.owning_squad,
        consumingSquad: localSquad,
      });

      if (!bridgeValidation.valid) {
        contractErrors.push({
          code: 'WF_CROSS_SQUAD_BRIDGE_INVALID',
          message: `Local bridge "${localBridgeRelativePath}" for cross-squad agent "${entry.agent}" is structurally incomplete`,
          suggestion: `Add the missing bridge contract snippets: ${bridgeValidation.missing.join(', ')}`,
          file: path.basename(workflowAbsPath),
        });
        continue;
      }
    }

    resolvedAgents.push({
      agent: entry.agent,
      owning_squad: entry.owning_squad,
      canonical_agent_path: canonicalRelativePath.split(path.sep).join('/'),
      local_bridge_path: localBridgeExists ? localBridgeRelativePath.split(path.sep).join('/') : null,
      evidence_sources: entry.evidence_sources,
    });
  }

  const filteredWarnings = (result.warnings || []).filter((warning) => {
    if (warning.code !== 'WF_AGENT_NOT_FOUND') {
      return true;
    }

    for (const agentName of suppressWarningsForAgents) {
      if (warningMatchesAgent(warning.message, agentName)) {
        return false;
      }
    }

    return true;
  });

  const mergedErrors = [...(result.errors || []), ...contractErrors];

  return {
    ...result,
    valid: mergedErrors.length === 0,
    errors: mergedErrors,
    warnings: filteredWarnings,
    cross_squad_contract: {
      checked_agents: crossSquadAgents.length,
      resolved_agents: resolvedAgents,
      errors: contractErrors,
    },
  };
}

module.exports = {
  applyCrossSquadContract,
  collectCrossSquadAgents,
  validateBridgeContent,
};
