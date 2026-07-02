/**
 * OpenCode Command Adapter
 *
 * Formats commands for OpenCode following its frontmatter specification.
 */
import path from 'path';
import { transformToHyphenCommands } from '../../../utils/command-references.js';
/**
 * OpenCode adapter for command generation.
 * File path: .opencode/commands/opsx-<id>.md
 * Frontmatter: description
 */
export const opencodeAdapter = {
    toolId: 'opencode',
    getFilePath(commandId) {
        return path.join('.opencode', 'commands', `opsx-${commandId}.md`);
    },
    formatFile(content) {
        // Transform command references from colon to hyphen format for OpenCode
        const transformedBody = transformToHyphenCommands(content.body);
        return `---
description: ${content.description}
---

${transformedBody}
`;
    },
};
//# sourceMappingURL=opencode.js.map