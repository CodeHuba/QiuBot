export declare const GLOBAL_CONFIG_DIR_NAME = "openspec";
export declare const GLOBAL_CONFIG_FILE_NAME = "config.json";
export declare const GLOBAL_DATA_DIR_NAME = "openspec";
export type Profile = 'core' | 'custom';
export type Delivery = 'both' | 'skills' | 'commands';
export interface GlobalConfig {
    featureFlags?: Record<string, boolean>;
    profile?: Profile;
    delivery?: Delivery;
    workflows?: string[];
    /** Workset opener rows (slice 7.1); hand-edited, validated on use. */
    openers?: unknown;
}
/**
 * Gets the global configuration directory path following XDG Base Directory Specification.
 *
 * - All platforms: $XDG_CONFIG_HOME/openspec/ if XDG_CONFIG_HOME is set
 * - Unix/macOS fallback: ~/.config/openspec/
 * - Windows fallback: %APPDATA%/openspec/
 */
export declare function getGlobalConfigDir(): string;
/**
 * Gets the global data directory path following XDG Base Directory Specification.
 * Used for user data like schema overrides.
 *
 * - All platforms: $XDG_DATA_HOME/openspec/ if XDG_DATA_HOME is set
 * - Unix/macOS fallback: ~/.local/share/openspec/
 * - Windows fallback: %LOCALAPPDATA%/openspec/
 */
export interface GlobalDataDirOptions {
    env?: NodeJS.ProcessEnv;
    platform?: NodeJS.Platform;
    homedir?: string;
}
export declare function getGlobalDataDir(options?: GlobalDataDirOptions): string;
/**
 * Gets the path to the global config file.
 */
export declare function getGlobalConfigPath(): string;
/**
 * Loads the global configuration from disk.
 * Returns default configuration if file doesn't exist or is invalid.
 * Merges loaded config with defaults to ensure new fields are available.
 */
export declare function getGlobalConfig(): GlobalConfig;
/**
 * Saves the global configuration to disk.
 * Creates the config directory if it doesn't exist.
 */
export declare function saveGlobalConfig(config: GlobalConfig): void;
//# sourceMappingURL=global-config.d.ts.map