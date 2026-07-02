/**
 * Qoder Command Adapter
 *
 * Formats commands for Qoder following its frontmatter specification.
 */
import path from 'path';
/**
 * Qoder adapter for command generation.
 * File path: .qoder/commands/opsx/<id>.md
 * Frontmatter: name, description, category, tags
 */
export const qoderAdapter = {
    toolId: 'qoder',
    getFilePath(commandId) {
        return path.join('.qoder', 'commands', 'opsx', `${commandId}.md`);
    },
    formatFile(content) {
        const tagsStr = content.tags.join(', ');
        return `---
name: ${content.name}
description: ${content.description}
category: ${content.category}
tags: [${tagsStr}]
---

${content.body}
`;
    },
};
//# sourceMappingURL=qoder.js.map