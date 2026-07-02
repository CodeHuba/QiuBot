/**
 * Update Command
 *
 * Refreshes OpenSpec skills and commands for configured tools.
 * Supports profile-aware updates, delivery changes, migration, and smart update detection.
 */
/**
 * Options for the update command.
 */
export interface UpdateCommandOptions {
    /** Force update even when tools are up to date */
    force?: boolean;
}
/**
 * Scans installed workflow artifacts (skills and managed commands) across all configured tools.
 * Returns the union of detected workflow IDs that match ALL_WORKFLOWS.
 *
 * Wrapper around the shared migration module's scanInstalledWorkflows that accepts tool IDs.
 */
export declare function scanInstalledWorkflows(projectPath: string, toolIds: string[]): string[];
export declare class UpdateCommand {
    private readonly force;
    constructor(options?: UpdateCommandOptions);
    execute(projectPath: string): Promise<void>;
    /**
     * Display message when all tools are up to date.
     */
    private displayUpToDateMessage;
    /**
     * Display the update plan showing which tools need updating.
     */
    private displayUpdatePlan;
    /**
     * Detects new tool directories that aren't currently configured and displays a hint.
     */
    private detectNewTools;
    /**
     * Displays a note about extra workflows installed that aren't in the current profile.
     */
    private displayExtraWorkflowsNote;
    /**
     * Suggest opting back into core when a custom profile still matches the old
     * pre-sync core set. Keep custom profiles user-owned; do not mutate them.
     */
    private displayOldCoreCustomProfileNote;
    /**
     * Removes skill directories for workflows when delivery changed to commands-only.
     * Returns the number of directories removed.
     */
    private removeSkillDirs;
    /**
     * Removes skill directories for workflows that are no longer selected in the active profile.
     * Returns the number of directories removed.
     */
    private removeUnselectedSkillDirs;
    /**
     * Removes command files for workflows when delivery changed to skills-only.
     * Returns the number of files removed.
     */
    private removeCommandFiles;
    /**
     * Removes command files for workflows that are no longer selected in the active profile.
     * Returns the number of files removed.
     */
    private removeUnselectedCommandFiles;
    /**
     * Detect and handle legacy OpenSpec artifacts.
     * Unlike init, update warns but continues if legacy files found in non-interactive mode.
     * Returns array of tool IDs that were newly configured during legacy upgrade.
     */
    private handleLegacyCleanup;
    /**
     * Perform cleanup of legacy artifacts.
     */
    private performLegacyCleanup;
    /**
     * Upgrade legacy tools to new skills system.
     * Returns array of tool IDs that were newly configured.
     */
    private upgradeLegacyTools;
}
//# sourceMappingURL=update.d.ts.map