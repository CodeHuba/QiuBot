import { Command } from 'commander';
declare const program: Command;
/**
 * Get the full command path for nested commands.
 * For example: 'change show' -> 'change:show'
 */
export declare function getCommandPath(command: Command): string;
export { program };
export declare function runCli(argv?: string[]): void;
//# sourceMappingURL=index.d.ts.map