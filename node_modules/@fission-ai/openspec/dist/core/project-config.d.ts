import { z } from 'zod';
/**
 * Zod schema for project configuration.
 *
 * Purpose:
 * 1. Documentation - clearly defines the config file structure
 * 2. Type safety - TypeScript infers ProjectConfig type from schema
 * 3. Runtime validation - uses safeParse() for resilient field-by-field validation
 *
 * Why Zod over manual validation:
 * - Helps understand OpenSpec's data interfaces at a glance
 * - Single source of truth for type and validation
 * - Consistent with other OpenSpec schemas
 */
export declare const ProjectConfigSchema: z.ZodObject<{
    schema: z.ZodString;
    context: z.ZodOptional<z.ZodString>;
    rules: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodArray<z.ZodString>>>;
    store: z.ZodOptional<z.ZodString>;
}, z.core.$strip>;
/** Normalized in-memory shape of a referenced store declaration. */
export interface DeclarationEntry {
    id: string;
    /** Clone source rendered into onboarding fixes. */
    remote?: string;
}
export type ProjectConfig = z.infer<typeof ProjectConfigSchema> & {
    references?: DeclarationEntry[];
};
export declare const MAX_CONTEXT_SIZE: number;
/**
 * Read and parse openspec/config.yaml from project root.
 * Uses resilient parsing - validates each field independently using Zod safeParse.
 * Returns null if file doesn't exist.
 * Returns partial config if some fields are invalid (with warnings).
 *
 * Performance note (Jan 2025):
 * Benchmarks showed direct file reads are fast enough without caching:
 * - Typical config (1KB): ~0.5ms per read
 * - Large config (50KB): ~1.6ms per read
 * - Missing config: ~0.01ms per read
 * Config is read 1-2 times per command (schema resolution + instruction loading),
 * adding ~1-3ms total overhead. Caching would add complexity (mtime checks,
 * invalidation logic) for negligible benefit. Direct reads also ensure config
 * changes are reflected immediately without stale cache issues.
 *
 * @param projectRoot - The root directory of the project (where `openspec/` lives)
 * @returns Parsed config or null if file doesn't exist
 */
export declare function readProjectConfig(projectRoot: string): ProjectConfig | null;
/**
 * Validate artifact IDs in rules against a schema's artifacts.
 * Called during instruction loading (when schema is known).
 * Returns warnings for unknown artifact IDs.
 *
 * @param rules - The rules object from config
 * @param validArtifactIds - Set of valid artifact IDs from the schema
 * @param schemaName - Name of the schema for error messages
 * @returns Array of warning messages for unknown artifact IDs
 */
export declare function validateConfigRules(rules: Record<string, string[]>, validArtifactIds: Set<string>, schemaName: string): string[];
/**
 * Suggest valid schema names when user provides invalid schema.
 * Uses fuzzy matching to find similar names.
 *
 * @param invalidSchemaName - The invalid schema name from config
 * @param availableSchemas - List of available schemas with their type (built-in or project-local)
 * @returns Error message with suggestions and available schemas
 */
export declare function suggestSchemas(invalidSchemaName: string, availableSchemas: {
    name: string;
    isBuiltIn: boolean;
}[]): string;
export interface StorePointerRead {
    /** The declared store id, when present and a string. */
    value?: string;
    /** Set when the pointer cannot be trusted: the config file could not be
     * read as YAML, or the store key is present but not a string. An empty
     * or comments-only config is NOT malformed - it simply has no pointer. */
    malformed?: 'unparseable' | 'non_string';
    /** Absolute path of the config file actually read, or null when none exists. */
    filePath: string | null;
}
/**
 * Warning-silent targeted read of the `store:` pointer. Used by root
 * resolution (which must not re-emit the resilient parser's field
 * warnings) and by `openspec init`'s pointer guard. Unlike
 * `readProjectConfig`, a malformed value is REPORTED, not dropped —
 * a dropped pointer would silently flip where work lands.
 */
export declare function readStorePointer(projectRoot: string): StorePointerRead;
/** Shared .yaml/.yml probe used by readProjectConfig and readStorePointer. */
export declare function resolveConfigFilePath(projectRoot: string): string | null;
/** Human rendering of a malformed pointer reason, shared by every surface. */
export declare function storePointerProblem(reason: 'unparseable' | 'non_string'): string;
export interface OpenSpecDirClassification {
    /** True when openspec/specs or openspec/changes exists as a directory. */
    hasPlanningShape: boolean;
    pointer: StorePointerRead;
}
/**
 * One classification for "real root vs config-only pointer dir", shared
 * by root resolution and the init pointer guard so they can never
 * disagree (slice 3.2).
 */
export declare function classifyOpenSpecDir(projectRoot: string): OpenSpecDirClassification;
//# sourceMappingURL=project-config.d.ts.map