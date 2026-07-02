import { Command } from 'commander';
import { GlobalConfig } from '../core/global-config.js';
import type { Profile, Delivery } from '../core/global-config.js';
interface ProfileState {
    profile: Profile;
    delivery: Delivery;
    workflows: string[];
}
interface ProfileStateDiff {
    hasChanges: boolean;
    lines: string[];
}
/**
 * Resolve the effective current profile state from global config defaults.
 */
export declare function resolveCurrentProfileState(config: GlobalConfig): ProfileState;
/**
 * Derive profile type from selected workflows.
 */
export declare function deriveProfileFromWorkflowSelection(selectedWorkflows: string[]): Profile;
/**
 * Format a compact workflow summary for the profile header.
 */
export declare function formatWorkflowSummary(workflows: readonly string[], profile: Profile): string;
/**
 * Build a user-facing diff summary between two profile states.
 */
export declare function diffProfileState(before: ProfileState, after: ProfileState): ProfileStateDiff;
/**
 * Register the config command and all its subcommands.
 *
 * @param program - The Commander program instance
 */
export declare function registerConfigCommand(program: Command): void;
export {};
//# sourceMappingURL=config.d.ts.map