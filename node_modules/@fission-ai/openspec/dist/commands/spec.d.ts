import { program } from 'commander';
import type { RootOutput } from '../core/root-selection.js';
interface ShowOptions {
    json?: boolean;
    requirements?: boolean;
    scenarios?: boolean;
    requirement?: string;
    noInteractive?: boolean;
    rootOutput?: RootOutput;
}
export declare class SpecCommand {
    private specsDir;
    private rootPath?;
    constructor(rootPath?: string);
    show(specId?: string, options?: ShowOptions): Promise<void>;
}
export declare function registerSpecCommand(rootProgram: typeof program): import("commander").Command;
export {};
//# sourceMappingURL=spec.d.ts.map