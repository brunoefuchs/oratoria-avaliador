#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const YAML = require("yaml");

function parseArgs(argv) {
  const args = {
    squads: [],
    strict: false,
    failOnWarnings: false,
    json: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--squads" && argv[i + 1]) {
      args.squads = argv[i + 1]
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
      i += 1;
    } else if (arg === "--strict") {
      args.strict = true;
    } else if (arg === "--fail-on-warnings") {
      args.failOnWarnings = true;
    } else if (arg === "--json") {
      args.json = true;
    }
  }

  return args;
}

function collectWorkflowFiles(dir) {
  if (!fs.existsSync(dir)) {
    return [];
  }

  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && /\.(ya?ml)$/i.test(entry.name))
    .map((entry) => path.join(dir, entry.name))
    .sort();
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function resolveStepId(step) {
  if (!step || typeof step !== "object" || Array.isArray(step)) {
    return "";
  }

  if (isNonEmptyString(step.id)) return step.id;
  if (isNonEmptyString(step.step_id)) return step.step_id;
  if (isNonEmptyString(step.step)) return step.step;
  if (isNonEmptyString(step.phase_id)) return step.phase_id;
  if (isNonEmptyString(step.name)) return step.name;
  if (typeof step.phase === "string" && step.phase.trim().length > 0) return step.phase;
  if (typeof step.phase === "number") return String(step.phase);
  return "";
}

function hasStepExecutor(step) {
  if (isNonEmptyString(step.agent)) {
    return true;
  }

  if (step.agents && typeof step.agents === "object" && !Array.isArray(step.agents)) {
    return true;
  }

  if (isNonEmptyString(step.executor_type)) {
    return true;
  }

  if (Array.isArray(step.agents) && step.agents.some((value) => isNonEmptyString(value))) {
    return true;
  }

  if (Array.isArray(step.atoms) && step.atoms.length > 0) {
    return true;
  }

  if (isNonEmptyString(step.command) || isNonEmptyString(step.logic)) {
    return true;
  }

  return false;
}

function hasStepSemantics(step) {
  if (Array.isArray(step.sub_phases) && step.sub_phases.length > 0) {
    return true;
  }

  if (Array.isArray(step.actions) && step.actions.some((value) => isNonEmptyString(value))) {
    return true;
  }

  if (isNonEmptyString(step.action)) {
    return true;
  }

  if (Array.isArray(step.outputs) && step.outputs.length > 0) {
    return true;
  }

  if (isNonEmptyString(step.output) || isNonEmptyString(step.output_path)) {
    return true;
  }

  if (isNonEmptyString(step.template) || isNonEmptyString(step.format)) {
    return true;
  }

  if (step.checkpoint && typeof step.checkpoint === "object" && !Array.isArray(step.checkpoint)) {
    return true;
  }

  if (Array.isArray(step.molecules) && step.molecules.length > 0) {
    return true;
  }

  if (
    step.framework_selection &&
    typeof step.framework_selection === "object" &&
    !Array.isArray(step.framework_selection) &&
    Object.keys(step.framework_selection).length > 0
  ) {
    return true;
  }

  if (
    step.optional_specialists &&
    typeof step.optional_specialists === "object" &&
    !Array.isArray(step.optional_specialists) &&
    Object.keys(step.optional_specialists).length > 0
  ) {
    return true;
  }

  return false;
}

function validateStep(step, index, filePath) {
  const errors = [];

  if (typeof step === "string" && step.trim().length > 0) {
    return errors;
  }

  if (!step || typeof step !== "object" || Array.isArray(step)) {
    errors.push(`step[${index}] in ${filePath} must be an object`);
    return errors;
  }

  if (step.workflow_end || step.repeat_development_cycle || step.import) {
    return errors;
  }

  if (!isNonEmptyString(resolveStepId(step))) {
    errors.push(`step[${index}] in ${filePath} is missing id`);
  }

  if (!hasStepExecutor(step) && !hasStepSemantics(step)) {
    errors.push(`step[${index}] in ${filePath} is missing agent or executable semantics`);
  }

  return errors;
}

function resolveWorkflowSequence(candidate) {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
    return [];
  }

  for (const key of ["sequence", "steps", "phases"]) {
    const value = candidate[key];
    if (Array.isArray(value)) {
      return value;
    }
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return Object.values(value).filter((item) => item && typeof item === "object");
    }
  }

  return [];
}

function looksLikeAuxiliaryWorkflowFile(parsed) {
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return false;
  }

  const keys = Object.keys(parsed);
  if (keys.length === 0) {
    return false;
  }

  if (parsed.quality_gates && !parsed.workflow && !parsed.workflows && !parsed.workflow_definition) {
    return true;
  }

  if (parsed.workflow_thresholds && !parsed.workflow && !parsed.workflows && !parsed.workflow_definition) {
    return true;
  }

  const auxiliaryKeys = new Set([
    "quality_gates",
    "workflow_thresholds",
    "thresholds",
    "checkpoint_self_eval",
    "metadata",
    "process_name",
    "process_slug",
    "gate_coverage",
    "critical_transitions",
    "current_readiness_prediction",
  ]);

  return keys.every((key) => auxiliaryKeys.has(key));
}

function collectWorkflowCandidates(parsed) {
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return [];
  }

  const candidates = [];

  const workflowObject =
    parsed.workflow && typeof parsed.workflow === "object" && !Array.isArray(parsed.workflow)
      ? parsed.workflow
      : null;

  if (workflowObject) {
    candidates.push({
      ...workflowObject,
      id:
        workflowObject.id ||
        parsed.id ||
        parsed.metadata?.id ||
        workflowObject.name ||
        parsed.name ||
        parsed.metadata?.name,
      name: workflowObject.name || parsed.name || parsed.metadata?.name || workflowObject.id || parsed.id,
      sequence:
        resolveWorkflowSequence(workflowObject).length > 0
          ? resolveWorkflowSequence(workflowObject)
          : resolveWorkflowSequence(parsed),
    });
  }

  if (
    !workflowObject &&
    (isNonEmptyString(parsed.workflow) || isNonEmptyString(parsed.name) || isNonEmptyString(parsed.id)) &&
    resolveWorkflowSequence(parsed).length > 0
  ) {
    candidates.push({
      ...parsed,
      id: isNonEmptyString(parsed.id) ? parsed.id : parsed.workflow || parsed.name,
      name: parsed.name || parsed.workflow || parsed.id,
    });
  }

  if (Array.isArray(parsed.workflows)) {
    for (const workflow of parsed.workflows) {
      if (workflow && typeof workflow === "object" && !Array.isArray(workflow)) {
        candidates.push({
          ...workflow,
          id: isNonEmptyString(workflow.id) ? workflow.id : workflow.workflow_id || workflow.name,
          sequence: resolveWorkflowSequence(workflow),
        });
      }
    }
  }

  if (parsed.workflow_definition && typeof parsed.workflow_definition === "object" && !Array.isArray(parsed.workflow_definition)) {
    const wrapper = parsed.workflow_definition;
    if (Array.isArray(wrapper.workflows)) {
      for (const workflow of wrapper.workflows) {
        if (workflow && typeof workflow === "object" && !Array.isArray(workflow)) {
          candidates.push({
            ...workflow,
            id: workflow.id || workflow.workflow_id || wrapper.instance_id || workflow.name,
            name: workflow.name || workflow.workflow_id || wrapper.template_name || wrapper.instance_id,
            sequence: resolveWorkflowSequence(workflow),
          });
        }
      }
    } else if (resolveWorkflowSequence(wrapper).length > 0) {
      candidates.push({
        ...wrapper,
        id: wrapper.id || wrapper.instance_id || wrapper.template_id || wrapper.template_name,
        name: wrapper.name || wrapper.template_name || wrapper.instance_id || wrapper.template_id,
        sequence: resolveWorkflowSequence(wrapper),
      });
    }
  }

  if (!workflowObject && parsed.metadata && typeof parsed.metadata === "object" && resolveWorkflowSequence(parsed).length > 0) {
    candidates.push({
      ...parsed,
      id: parsed.id || parsed.metadata.id || parsed.name || parsed.metadata.name,
      name: parsed.name || parsed.metadata.name || parsed.id || parsed.metadata.id,
      sequence: resolveWorkflowSequence(parsed),
    });
  }

  if (
    !workflowObject &&
    parsed.actions &&
    typeof parsed.actions === "object" &&
    !Array.isArray(parsed.actions)
  ) {
    for (const [actionId, actionConfig] of Object.entries(parsed.actions)) {
      if (!actionConfig || typeof actionConfig !== "object" || Array.isArray(actionConfig)) {
        continue;
      }
      if (!Array.isArray(actionConfig.steps) || actionConfig.steps.length === 0) {
        continue;
      }
      candidates.push({
        id: actionId,
        name: actionConfig.description || actionId,
        sequence: actionConfig.steps,
      });
    }
  }

  return candidates;
}

function validateWorkflowCandidate(candidate, filePath, candidateIndex = 0) {
  const errors = [];
  const warnings = [];
  const label = candidateIndex > 0 ? `${filePath}#${candidateIndex + 1}` : filePath;

  if (!isNonEmptyString(candidate.id)) {
    errors.push(`workflow.id is required in ${label}`);
  }

  if (!isNonEmptyString(candidate.name)) {
    errors.push(`workflow.name is required in ${label}`);
  }

  const sequence = resolveWorkflowSequence(candidate);
  if (!Array.isArray(sequence) || sequence.length === 0) {
    errors.push(`workflow.sequence must contain at least one step in ${label}`);
    return { errors, warnings };
  }

  sequence.forEach((step, index) => {
    errors.push(...validateStep(step, index, label));
  });

  return { errors, warnings };
}

function validateWorkflowFile(filePath) {
  let parsed;
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    const docs = YAML.parseAllDocuments(raw);
    const objects = docs
      .map((doc) => {
        if (doc.errors && doc.errors.length > 0) {
          throw new Error(doc.errors[0].message);
        }
        return doc.toJSON();
      })
      .filter((value) => value && typeof value === "object" && !Array.isArray(value));

    if (objects.length === 0) {
      parsed = YAML.parse(raw);
    } else if (objects.length === 1) {
      parsed = objects[0];
    } else {
      parsed = Object.assign({}, ...objects);
    }
  } catch (error) {
    return { errors: [`invalid YAML: ${error.message}`], warnings: [] };
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { errors: ["root payload must be an object"], warnings: [] };
  }

  if (looksLikeAuxiliaryWorkflowFile(parsed)) {
    return { errors: [], warnings: [], skipped: true };
  }

  const candidates = collectWorkflowCandidates(parsed);
  if (candidates.length === 0) {
    return { errors: ["missing workflow root object"], warnings: [] };
  }

  const errors = [];
  const warnings = [];
  candidates.forEach((candidate, index) => {
    const outcome = validateWorkflowCandidate(candidate, filePath, index);
    errors.push(...outcome.errors);
    warnings.push(...outcome.warnings);
  });

  return { errors, warnings };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const repoRoot = path.resolve(__dirname, "../../..");
  const requestedSquads = args.squads.length > 0 ? args.squads : [];

  if (requestedSquads.length === 0) {
    console.error("Missing required --squads argument");
    process.exit(1);
  }

  const results = [];

  for (const squadName of requestedSquads) {
    const workflowsDir = path.join(repoRoot, "squads", squadName, "workflows");
    const files = collectWorkflowFiles(workflowsDir);

    for (const filePath of files) {
      const outcome = validateWorkflowFile(filePath);
      if (outcome.skipped) {
        continue;
      }
      results.push({
        squad: squadName,
        file: path.relative(repoRoot, filePath),
        errors: outcome.errors,
        warnings: outcome.warnings,
        status: outcome.errors.length === 0 && outcome.warnings.length === 0 ? "PASS" : "FAIL",
      });
    }
  }

  const totals = {
    files_checked: results.length,
    errors: results.reduce((sum, result) => sum + result.errors.length, 0),
    warnings: results.reduce((sum, result) => sum + result.warnings.length, 0),
    invalid_files: results.filter((result) => result.errors.length > 0).length,
  };

  const payload = {
    totals,
    results,
  };

  if (args.json) {
    console.log(JSON.stringify(payload, null, 2));
  } else {
    for (const result of results) {
      console.log(`${result.status} ${result.file}`);
      for (const error of result.errors) {
        console.log(`  ERROR: ${error}`);
      }
      for (const warning of result.warnings) {
        console.log(`  WARN: ${warning}`);
      }
    }
    console.log(JSON.stringify({ totals }, null, 2));
  }

  const shouldFail = totals.errors > 0 || (args.failOnWarnings && totals.warnings > 0);
  process.exit(shouldFail ? 1 : 0);
}

main();
