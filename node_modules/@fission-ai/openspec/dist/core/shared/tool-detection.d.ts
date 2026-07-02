/**
 * Tool Detection Utilities
 *
 * Shared utilities for detecting tool configurations and version status.
 */
/**
 * Names of skill directories created by openspec init.
 */
export declare const SKILL_NAMES: readonly ["openspec-explore", "openspec-new-change", "openspec-continue-change", "openspec-apply-change", "openspec-ff-change", "openspec-sync-specs", "openspec-archive-change", "openspec-bulk-archive-change", "openspec-verify-change", "openspec-onboard", "openspec-propose"];
export type SkillName = (typeof SKILL_NAMES)[number];
/**
 * IDs of command templates created by openspec init.
 */
export declare const COMMAND_IDS: readonly ["explore", "new", "continue", "apply", "ff", "sync", "archive", "bulk-archive", "verify", "onboard", "propose"];
export type CommandId = (typeof COMMAND_IDS)[number];
/**
 * Status of skill configuration for a tool.
 */
export interface ToolSkillStatus {
    /** Whether the tool has any skills configured */
    configured: boolean;
    /** Whether all skills are configured */
    fullyConfigured: boolean;
    /** Number of skills currently configured */
    skillCount: number;
}
/**
 * Version information for a tool's skills.
 */
export interface ToolVersionStatus {
    /** The tool ID */
    toolId: string;
    /** The tool's display name */
    toolName: string;
    /** Whether the tool has any skills configured */
    configured: boolean;
    /** The generatedBy version found in the skill files, or null if not found */
    generatedByVersion: string | null;
    /** Whether the tool needs updating (version mismatch or missing) */
    needsUpdate: boolean;
}
/**
 * Gets the list of tools with skillsDir configured.
 */
export declare function getToolsWithSkillsDir(): string[];
/**
 * Checks which skill files exist for a tool.
 */
export declare function getToolSkillStatus(projectRoot: string, toolId: string): ToolSkillStatus;
/**
 * Gets the skill status for all tools with skillsDir configured.
 */
export declare function getToolStates(projectRoot: string): Map<string, ToolSkillStatus>;
/**
 * Extracts the generatedBy version from a skill file's YAML frontmatter.
 * Returns null if the field is not found or the file doesn't exist.
 */
export declare function extractGeneratedByVersion(skillFilePath: string): string | null;
/**
 * Gets version status for a tool by reading the first available skill file.
 */
export declare function getToolVersionStatus(projectRoot: string, toolId: string, currentVersion: string): ToolVersionStatus;
/**
 * Gets all configured tools in the project.
 */
export declare function getConfiguredTools(projectRoot: string): string[];
/**
 * Gets version status for all configured tools.
 */
export declare function getAllToolVersionStatus(projectRoot: string, currentVersion: string): ToolVersionStatus[];
//# sourceMappingURL=tool-detection.d.ts.map