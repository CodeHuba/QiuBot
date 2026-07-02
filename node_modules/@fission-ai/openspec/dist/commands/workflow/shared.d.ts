/**
 * Shared Types and Utilities for Artifact Workflow Commands
 *
 * This module contains types, constants, and validation helpers used across
 * multiple artifact workflow commands.
 */
import type { ReferenceIndexEntry } from '../../core/references.js';
export interface ChangeCommandStatus {
    severity: 'error' | 'warning';
    code: string;
    message: string;
    target?: string;
    fix?: string;
}
export interface TaskItem {
    id: string;
    description: string;
    done: boolean;
}
export interface ApplyInstructions {
    changeName: string;
    changeDir: string;
    schemaName: string;
    contextFiles: Record<string, string[]>;
    progress: {
        total: number;
        complete: number;
        remaining: number;
    };
    tasks: TaskItem[];
    state: 'blocked' | 'all_done' | 'ready';
    missingArtifacts?: string[];
    instruction: string;
    /** Referenced-store index (read-only upstream context; omitted when none declared) */
    references?: ReferenceIndexEntry[];
}
export declare const DEFAULT_SCHEMA = "spec-driven";
export declare function printJson(payload: unknown): void;
export declare function statusFromError(error: unknown): ChangeCommandStatus;
/**
 * Checks if color output is disabled via NO_COLOR env or --no-color flag.
 */
export declare function isColorDisabled(): boolean;
/**
 * Gets the color function based on status.
 */
export declare function getStatusColor(status: 'done' | 'ready' | 'blocked'): (text: string) => string;
/**
 * Gets the status indicator for an artifact.
 */
export declare function getStatusIndicator(status: 'done' | 'ready' | 'blocked'): string;
/**
 * Returns the list of available change directory names under openspec/changes/.
 * Excludes the archive directory and hidden directories.
 */
export declare function getAvailableChanges(projectRoot: string, changesDir?: string): Promise<string[]>;
/**
 * Validates that a change exists and returns available changes if not.
 * Checks directory existence directly to support scaffolded changes (without proposal.md).
 */
export declare function validateChangeExists(changeName: string | undefined, projectRoot: string, changesDir?: string, hints?: {
    newChangeHint?: string;
}): Promise<string>;
/**
 * Validates that a schema exists and returns available schemas if not.
 *
 * @param schemaName - The schema name to validate
 * @param projectRoot - Optional project root for project-local schema resolution
 */
export declare function validateSchemaExists(schemaName: string, projectRoot?: string): string;
//# sourceMappingURL=shared.d.ts.map