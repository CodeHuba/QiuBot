/**
 * Migration Utilities
 *
 * One-time migration logic for existing projects when profile system is introduced.
 * Called by both init and update commands before profile resolution.
 */
import type { AIToolOption } from './config.js';
/**
 * Scans installed workflow files across all detected tools and returns
 * the union of installed workflow IDs.
 */
export declare function scanInstalledWorkflows(projectPath: string, tools: AIToolOption[]): string[];
/**
 * Performs one-time migration if the global config does not yet have a profile field.
 * Called by both init and update before profile resolution.
 *
 * - If no profile field exists and workflows are installed: sets profile to 'custom'
 *   with the detected workflows, preserving the user's existing setup.
 * - If no profile field exists and no workflows are installed: no-op (defaults apply).
 * - If profile field already exists: no-op.
 */
export declare function migrateIfNeeded(projectPath: string, tools: AIToolOption[]): void;
//# sourceMappingURL=migration.d.ts.map