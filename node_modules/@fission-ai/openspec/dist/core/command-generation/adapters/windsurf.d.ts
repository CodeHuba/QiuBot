/**
 * Windsurf Command Adapter
 *
 * Formats commands for Windsurf following its frontmatter specification.
 * Windsurf uses a similar format to Claude but may have different conventions.
 */
import type { ToolCommandAdapter } from '../types.js';
/**
 * Windsurf adapter for command generation.
 * File path: .windsurf/workflows/opsx-<id>.md
 * Frontmatter: name, description, category, tags
 */
export declare const windsurfAdapter: ToolCommandAdapter;
//# sourceMappingURL=windsurf.d.ts.map