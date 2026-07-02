/**
 * Codex Command Adapter
 *
 * Formats commands for Codex following its frontmatter specification.
 * Codex custom prompts live in the global home directory (~/.codex/prompts/)
 * and are not shared through the repository. The CODEX_HOME env var can
 * override the default ~/.codex location.
 */
import os from 'os';
import path from 'path';
/**
 * Returns the Codex home directory.
 * Respects the CODEX_HOME env var, defaulting to ~/.codex.
 */
function getCodexHome() {
    const envHome = process.env.CODEX_HOME?.trim();
    return path.resolve(envHome ? envHome : path.join(os.homedir(), '.codex'));
}
/**
 * Codex adapter for command generation.
 * File path: <CODEX_HOME>/prompts/opsx-<id>.md (absolute, global)
 * Frontmatter: description, argument-hint
 */
export const codexAdapter = {
    toolId: 'codex',
    getFilePath(commandId) {
        return path.join(getCodexHome(), 'prompts', `opsx-${commandId}.md`);
    },
    formatFile(content) {
        return `---
description: ${content.description}
argument-hint: command arguments
---

${content.body}
`;
    },
};
//# sourceMappingURL=codex.js.map