/**
 * Crush Command Adapter
 *
 * Formats commands for Crush following its frontmatter specification.
 */
import path from 'path';
/**
 * Crush adapter for command generation.
 * File path: .crush/commands/opsx/<id>.md
 * Frontmatter: name, description, category, tags
 */
export const crushAdapter = {
    toolId: 'crush',
    getFilePath(commandId) {
        return path.join('.crush', 'commands', 'opsx', `${commandId}.md`);
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
//# sourceMappingURL=crush.js.map