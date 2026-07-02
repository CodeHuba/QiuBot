/**
 * Shared Types and Utilities for Artifact Workflow Commands
 *
 * This module contains types, constants, and validation helpers used across
 * multiple artifact workflow commands.
 */
import chalk from 'chalk';
import path from 'path';
import * as fs from 'fs';
import { getSchemaDir, listSchemas } from '../../core/artifact-graph/index.js';
import { isRootSelectionError } from '../../core/root-selection.js';
import { validateChangeName } from '../../utils/change-utils.js';
// -----------------------------------------------------------------------------
// Constants
// -----------------------------------------------------------------------------
export const DEFAULT_SCHEMA = 'spec-driven';
// -----------------------------------------------------------------------------
// Utility Functions
// -----------------------------------------------------------------------------
export function printJson(payload) {
    console.log(JSON.stringify(payload, null, 2));
}
export function statusFromError(error) {
    if (isRootSelectionError(error)) {
        return { ...error.diagnostic };
    }
    return {
        severity: 'error',
        code: 'change_error',
        message: error instanceof Error ? error.message : String(error),
    };
}
/**
 * Checks if color output is disabled via NO_COLOR env or --no-color flag.
 */
export function isColorDisabled() {
    return process.env.NO_COLOR === '1' || process.env.NO_COLOR === 'true';
}
/**
 * Gets the color function based on status.
 */
export function getStatusColor(status) {
    if (isColorDisabled()) {
        return (text) => text;
    }
    switch (status) {
        case 'done':
            return chalk.green;
        case 'ready':
            return chalk.yellow;
        case 'blocked':
            return chalk.red;
    }
}
/**
 * Gets the status indicator for an artifact.
 */
export function getStatusIndicator(status) {
    const color = getStatusColor(status);
    switch (status) {
        case 'done':
            return color('[x]');
        case 'ready':
            return color('[ ]');
        case 'blocked':
            return color('[-]');
    }
}
/**
 * Returns the list of available change directory names under openspec/changes/.
 * Excludes the archive directory and hidden directories.
 */
export async function getAvailableChanges(projectRoot, changesDir = path.join(projectRoot, 'openspec', 'changes')) {
    const changesPath = changesDir;
    try {
        const entries = await fs.promises.readdir(changesPath, { withFileTypes: true });
        return entries
            .filter((e) => e.isDirectory() && e.name !== 'archive' && !e.name.startsWith('.'))
            .map((e) => e.name);
    }
    catch (error) {
        if (error.code === 'ENOENT')
            return [];
        throw error;
    }
}
/**
 * Validates that a change exists and returns available changes if not.
 * Checks directory existence directly to support scaffolded changes (without proposal.md).
 */
export async function validateChangeExists(changeName, projectRoot, changesDir = path.join(projectRoot, 'openspec', 'changes'), hints = {}) {
    // Hints must stay pasteable: callers with a selected store pass a
    // store-carrying hint so following it lands in the same root.
    const newChangeHint = hints.newChangeHint ?? 'openspec new change <name>';
    if (!changeName) {
        const available = await getAvailableChanges(projectRoot, changesDir);
        if (available.length === 0) {
            throw new Error(`No changes found. Create one with: ${newChangeHint}`);
        }
        throw new Error(`Missing required option --change. Available changes:\n  ${available.join('\n  ')}`);
    }
    // Validate change name format to prevent path traversal
    const nameValidation = validateChangeName(changeName);
    if (!nameValidation.valid) {
        throw new Error(`Invalid change name '${changeName}': ${nameValidation.error}`);
    }
    // Check directory existence directly
    const changePath = path.join(changesDir, changeName);
    const exists = fs.existsSync(changePath) && fs.statSync(changePath).isDirectory();
    if (!exists) {
        const available = await getAvailableChanges(projectRoot, changesDir);
        if (available.length === 0) {
            throw new Error(`Change '${changeName}' not found. No changes exist. Create one with: ${newChangeHint}`);
        }
        throw new Error(`Change '${changeName}' not found. Available changes:\n  ${available.join('\n  ')}`);
    }
    return changeName;
}
/**
 * Validates that a schema exists and returns available schemas if not.
 *
 * @param schemaName - The schema name to validate
 * @param projectRoot - Optional project root for project-local schema resolution
 */
export function validateSchemaExists(schemaName, projectRoot) {
    const schemaDir = getSchemaDir(schemaName, projectRoot);
    if (!schemaDir) {
        const availableSchemas = listSchemas(projectRoot);
        throw new Error(`Schema '${schemaName}' not found. Available schemas:\n  ${availableSchemas.join('\n  ')}`);
    }
    return schemaName;
}
//# sourceMappingURL=shared.js.map