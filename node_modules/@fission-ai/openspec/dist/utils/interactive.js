/**
 * Resolves whether non-interactive mode is requested.
 * Handles both explicit `noInteractive: true` and Commander.js style `interactive: false`.
 * Use this helper instead of manually checking options.noInteractive to avoid bugs.
 */
export function resolveNoInteractive(value) {
    if (typeof value === 'boolean')
        return value;
    return value?.noInteractive === true || value?.interactive === false;
}
export function isInteractive(value) {
    if (resolveNoInteractive(value))
        return false;
    if (process.env.OPEN_SPEC_INTERACTIVE === '0')
        return false;
    // Respect the standard CI environment variable (set by GitHub Actions, GitLab CI, Travis, etc.)
    if ('CI' in process.env)
        return false;
    return !!process.stdin.isTTY;
}
//# sourceMappingURL=interactive.js.map