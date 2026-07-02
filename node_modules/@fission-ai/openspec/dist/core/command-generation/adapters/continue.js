/**
 * Continue Command Adapter
 *
 * Formats commands for Continue following its .prompt specification.
 */
import path from 'path';
/**
 * Continue adapter for command generation.
 * File path: .continue/prompts/opsx-<id>.prompt
 * Frontmatter: name, description, invokable
 */
export const continueAdapter = {
    toolId: 'continue',
    getFilePath(commandId) {
        return path.join('.continue', 'prompts', `opsx-${commandId}.prompt`);
    },
    formatFile(content) {
        return `---
name: opsx-${content.id}
description: ${content.description}
invokable: true
---

${content.body}
`;
    },
};
//# sourceMappingURL=continue.js.map