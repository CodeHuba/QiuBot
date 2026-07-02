/**
 * Checks if a path contains glob pattern characters.
 */
export declare function isGlobPattern(pattern: string): boolean;
/**
 * Resolves an artifact's output path(s) to concrete files that currently exist.
 * Returns absolute file paths. Glob matches are sorted for deterministic output.
 */
export declare function resolveArtifactOutputs(changeDir: string, generates: string): string[];
/**
 * Checks if an artifact has at least one resolved output file.
 */
export declare function artifactOutputExists(changeDir: string, generates: string): boolean;
//# sourceMappingURL=outputs.d.ts.map