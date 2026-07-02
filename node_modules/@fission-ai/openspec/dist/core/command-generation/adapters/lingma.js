/**
 * Lingma Command Adapter
 *
 * Formats commands for Lingma following its frontmatter specification.
 */
import path from 'path';
/**
 * Lingma adapter for command generation.
 * File path: .lingma/commands/opsx/<id>.md
 * Frontmatter: name, description, category, tags
 */
export const lingmaAdapter = {
    toolId: 'lingma',
    getFilePath(commandId) {
        return path.join('.lingma', 'commands', 'opsx', `${commandId}.md`);
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
//# sourceMappingURL=lingma.js.map