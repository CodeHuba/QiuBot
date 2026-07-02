/**
 * Status Command
 *
 * Displays artifact completion status for a change.
 */
import { type ChangeStatus } from '../../core/artifact-graph/index.js';
export interface StatusOptions {
    change?: string;
    schema?: string;
    store?: string;
    storePath?: string;
    json?: boolean;
}
export declare function statusCommand(options: StatusOptions): Promise<void>;
export declare function printStatusText(status: ChangeStatus): void;
//# sourceMappingURL=status.d.ts.map