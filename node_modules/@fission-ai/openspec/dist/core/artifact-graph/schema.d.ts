import { type SchemaYaml } from './types.js';
export declare class SchemaValidationError extends Error {
    constructor(message: string);
}
/**
 * Loads and validates an artifact schema from a YAML file.
 */
export declare function loadSchema(filePath: string): SchemaYaml;
/**
 * Parses and validates an artifact schema from YAML content.
 */
export declare function parseSchema(yamlContent: string): SchemaYaml;
//# sourceMappingURL=schema.d.ts.map