/**
 * GitHub Copilot Command Adapter
 *
 * Formats commands for GitHub Copilot following its .prompt.md specification.
 */
import path from 'path';
/**
 * GitHub Copilot adapter for command generation.
 * File path: .github/prompts/opsx-<id>.prompt.md
 * Frontmatter: description
 */
export const githubCopilotAdapter = {
    toolId: 'github-copilot',
    getFilePath(commandId) {
        return path.join('.github', 'prompts', `opsx-${commandId}.prompt.md`);
    },
    formatFile(content) {
        return `---
description: ${content.description}
---

${content.body}
`;
    },
};
//# sourceMappingURL=github-copilot.js.map