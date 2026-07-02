/**
 * Qwen Code Command Adapter
 *
 * Formats commands for Qwen Code following its TOML specification.
 */
import path from 'path';
/**
 * Qwen adapter for command generation.
 * File path: .qwen/commands/opsx-<id>.toml
 * Format: TOML with description and prompt fields
 */
export const qwenAdapter = {
    toolId: 'qwen',
    getFilePath(commandId) {
        return path.join('.qwen', 'commands', `opsx-${commandId}.toml`);
    },
    formatFile(content) {
        return `description = "${content.description}"

prompt = """
${content.body}
"""
`;
    },
};
//# sourceMappingURL=qwen.js.map