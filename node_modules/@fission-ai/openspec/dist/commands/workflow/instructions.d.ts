/**
 * Instructions Command
 *
 * Generates enriched instructions for creating artifacts or applying tasks.
 * Includes both artifact instructions and apply instructions.
 */
import { type ArtifactInstructions } from '../../core/artifact-graph/index.js';
import { type PlanningHome } from '../../core/planning-home.js';
import { type ReferenceIndexEntry } from '../../core/references.js';
import { type ApplyInstructions } from './shared.js';
export interface InstructionsOptions {
    change?: string;
    schema?: string;
    store?: string;
    storePath?: string;
    json?: boolean;
}
export interface ApplyInstructionsOptions {
    change?: string;
    schema?: string;
    store?: string;
    storePath?: string;
    json?: boolean;
}
export declare function instructionsCommand(artifactId: string | undefined, options: InstructionsOptions): Promise<void>;
export declare function printInstructionsText(instructions: ArtifactInstructions, isBlocked: boolean): void;
export interface GenerateApplyInstructionsOptions {
    planningHome?: PlanningHome;
    references?: ReferenceIndexEntry[];
}
/**
 * Generates apply instructions for implementing tasks from a change.
 * Schema-aware: reads apply phase configuration from schema to determine
 * required artifacts, tracking file, and instruction.
 */
export declare function generateApplyInstructions(projectRoot: string, changeName: string, schemaName?: string, options?: GenerateApplyInstructionsOptions): Promise<ApplyInstructions>;
export declare function applyInstructionsCommand(options: ApplyInstructionsOptions): Promise<void>;
export declare function printApplyInstructionsText(instructions: ApplyInstructions): void;
//# sourceMappingURL=instructions.d.ts.map