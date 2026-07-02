/**
 * Bob Shell Command Adapter
 *
 * Formats commands for Bob Shell following its markdown specification.
 * Commands are stored in .bob/commands/ directory.
 */
import path from 'path';
import { transformToHyphenCommands } from '../../../utils/command-references.js';
import { escapeYamlValue } from '../yaml.js';
/**
 * Bob Shell adapter for command generation.
 * File path: .bob/commands/opsx-<id>.md
 * Frontmatter: description, argument-hint
 */
export const bobAdapter = {
    toolId: 'bob',
    getFilePath(commandId) {
        return path.join('.bob', 'commands', `opsx-${commandId}.md`);
    },
    formatFile(content) {
        // Transform command references from colon to hyphen format for Bob
        const transformedBody = transformToHyphenCommands(content.body);
        return `---
description: ${escapeYamlValue(content.description)}
argument-hint: command arguments
---

${transformedBody}
`;
    },
};
//# sourceMappingURL=bob.js.map