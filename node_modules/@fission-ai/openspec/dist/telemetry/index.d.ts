/**
 * Check if telemetry is enabled.
 *
 * Disabled when:
 * - OPENSPEC_TELEMETRY=0
 * - DO_NOT_TRACK=1
 * - CI=true (any CI environment)
 */
export declare function isTelemetryEnabled(): boolean;
/**
 * Get or create the anonymous user ID.
 * Lazily generates a UUID on first call and persists it.
 */
export declare function getOrCreateAnonymousId(): Promise<string>;
/**
 * Track a command execution.
 *
 * @param commandName - The command name (e.g., 'init', 'change:apply')
 * @param version - The OpenSpec version
 */
export declare function trackCommand(commandName: string, version: string): Promise<void>;
/**
 * Show first-run telemetry notice if not already seen.
 */
export declare function maybeShowTelemetryNotice(): Promise<void>;
/**
 * Shutdown the PostHog client and flush pending events.
 * Call this before CLI exit.
 */
export declare function shutdown(): Promise<void>;
//# sourceMappingURL=index.d.ts.map