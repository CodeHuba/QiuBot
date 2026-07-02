import { type ChangeMetadata } from '../core/change-metadata/index.js';
export declare const METADATA_FILENAME = ".openspec.yaml";
/**
 * Error thrown when change metadata validation fails.
 */
export declare class ChangeMetadataError extends Error {
    readonly metadataPath: string;
    readonly cause?: Error | undefined;
    constructor(message: string, metadataPath: string, cause?: Error | undefined);
}
/**
 * Validates that a schema name is valid (exists in available schemas).
 *
 * @param schemaName - The schema name to validate
 * @param projectRoot - Optional project root for project-local schema resolution
 * @returns The validated schema name
 * @throws Error if schema is not found
 */
export declare function validateSchemaName(schemaName: string, projectRoot?: string): string;
/**
 * Writes change metadata to .openspec.yaml in the change directory.
 *
 * @param changeDir - The path to the change directory
 * @param metadata - The metadata to write
 * @param projectRoot - Optional project root for project-local schema resolution
 * @throws ChangeMetadataError if validation fails or write fails
 */
export declare function writeChangeMetadata(changeDir: string, metadata: ChangeMetadata, projectRoot?: string): void;
/**
 * Reads change metadata from .openspec.yaml in the change directory.
 *
 * @param changeDir - The path to the change directory
 * @param projectRoot - Optional project root for project-local schema resolution
 * @returns The validated metadata, or null if no metadata file exists
 * @throws ChangeMetadataError if the file exists but is invalid
 */
export declare function readChangeMetadata(changeDir: string, projectRoot?: string): ChangeMetadata | null;
export interface ResolveSchemaForChangeOptions {
    metadata?: ChangeMetadata | null;
}
/**
 * Resolves the schema for a change, with explicit override taking precedence.
 *
 * Resolution order:
 * 1. Explicit schema (if provided)
 * 2. Schema from .openspec.yaml metadata (if exists)
 * 3. Schema from openspec/config.yaml (if exists)
 * 4. Default 'spec-driven'
 *
 * @param changeDir - The path to the change directory
 * @param explicitSchema - Optional explicit schema override
 * @returns The resolved schema name
 */
export declare function resolveSchemaForChange(changeDir: string, explicitSchema?: string, projectRootOverride?: string, options?: ResolveSchemaForChangeOptions): string;
//# sourceMappingURL=change-metadata.d.ts.map