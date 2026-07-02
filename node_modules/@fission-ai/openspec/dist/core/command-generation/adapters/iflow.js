/**
 * iFlow Command Adapter
 *
 * Formats commands for iFlow following its frontmatter specification.
 */
import path from 'path';
/**
 * iFlow adapter for command generation.
 * File path: .iflow/commands/opsx-<id>.md
 * Frontmatter: name, id, category, description
 */
export const iflowAdapter = {
    toolId: 'iflow',
    getFilePath(commandId) {
        return path.join('.iflow', 'commands', `opsx-${commandId}.md`);
    },
    formatFile(content) {
        return `---
name: /opsx-${content.id}
id: opsx-${content.id}
category: ${content.category}
description: ${content.description}
---

${content.body}
`;
    },
};
//# sourceMappingURL=iflow.js.map