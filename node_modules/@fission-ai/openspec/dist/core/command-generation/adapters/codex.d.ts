/**
 * Codex Command Adapter
 *
 * Formats commands for Codex following its frontmatter specification.
 * Codex custom prompts live in the global home directory (~/.codex/prompts/)
 * and are not shared through the repository. The CODEX_HOME env var can
 * override the default ~/.codex location.
 */
import type { ToolCommandAdapter } from '../types.js';
/**
 * Codex adapter for command generation.
 * File path: <CODEX_HOME>/prompts/opsx-<id>.md (absolute, global)
 * Frontmatter: description, argument-hint
 */
export declare const codexAdapter: ToolCommandAdapter;
//# sourceMappingURL=codex.d.ts.map