/**
 * Amazon Q Developer Command Adapter
 *
 * Formats commands for Amazon Q Developer following its frontmatter specification.
 */
import path from 'path';
/**
 * Amazon Q adapter for command generation.
 * File path: .amazonq/prompts/opsx-<id>.md
 * Frontmatter: description
 */
export const amazonQAdapter = {
    toolId: 'amazon-q',
    getFilePath(commandId) {
        return path.join('.amazonq', 'prompts', `opsx-${commandId}.md`);
    },
    formatFile(content) {
        return `---
description: ${content.description}
---

${content.body}
`;
    },
};
//# sourceMappingURL=amazon-q.js.map