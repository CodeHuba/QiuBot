/**
 * Gemini CLI Command Adapter
 *
 * Formats commands for Gemini CLI following its TOML specification.
 */
import path from 'path';
/**
 * Gemini adapter for command generation.
 * File path: .gemini/commands/opsx/<id>.toml
 * Format: TOML with description and prompt fields
 */
export const geminiAdapter = {
    toolId: 'gemini',
    getFilePath(commandId) {
        return path.join('.gemini', 'commands', 'opsx', `${commandId}.toml`);
    },
    formatFile(content) {
        return `description = "${content.description}"

prompt = """
${content.body}
"""
`;
    },
};
//# sourceMappingURL=gemini.js.map