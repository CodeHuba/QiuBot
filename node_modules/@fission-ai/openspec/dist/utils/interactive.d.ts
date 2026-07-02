export type InteractiveOptions = {
    /**
     * Explicit "disable prompts" flag passed by internal callers.
     */
    noInteractive?: boolean;
    /**
     * Commander-style negated option: `--no-interactive` sets this to false.
     */
    interactive?: boolean;
};
/**
 * Resolves whether non-interactive mode is requested.
 * Handles both explicit `noInteractive: true` and Commander.js style `interactive: false`.
 * Use this helper instead of manually checking options.noInteractive to avoid bugs.
 */
export declare function resolveNoInteractive(value?: boolean | InteractiveOptions): boolean;
export declare function isInteractive(value?: boolean | InteractiveOptions): boolean;
//# sourceMappingURL=interactive.d.ts.map