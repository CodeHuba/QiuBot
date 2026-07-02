/**
 * Available Tools Detection
 *
 * Detects which AI tools are available in a project by scanning
 * for their configuration directories.
 */
import { type AIToolOption } from './config.js';
/**
 * Scans the project path for AI tool configuration directories and returns
 * the tools that are present.
 *
 * For tools with `detectionPaths`, checks those specific paths (files or
 * directories). Otherwise checks for the tool's `skillsDir` directory at
 * the project root. Only tools with a `skillsDir` property are considered.
 */
export declare function getAvailableTools(projectPath: string): AIToolOption[];
//# sourceMappingURL=available-tools.d.ts.map