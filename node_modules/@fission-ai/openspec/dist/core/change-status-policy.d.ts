import type { PlanningHome } from './planning-home.js';
export interface PlanningHomeSummary {
    kind: 'repo';
    root: string;
    changesDir: string;
    defaultSchema: string;
}
export interface ActionContext {
    mode: 'repo-local';
    sourceOfTruth: 'repo';
    planningArtifacts: string[];
    linkedContext: Array<{
        name: string;
    }>;
    allowedEditRoots: string[];
    requiresAffectedAreaSelection: boolean;
    constraints: string[];
}
export interface ChangeStatusPolicyArtifact {
    id: string;
    status: 'done' | 'ready' | 'blocked';
}
export interface ChangeNextStepsInput {
    changeName: string;
    artifactStatuses: ChangeStatusPolicyArtifact[];
    allArtifactsComplete: boolean;
    /** Selected store id; next-step commands must carry it. */
    storeId?: string;
}
export interface ActionContextInput {
    projectRoot: string;
    artifactIds: string[];
}
export declare function summarizePlanningHome(planningHome: PlanningHome | undefined): PlanningHomeSummary | undefined;
export declare function buildActionContext(input: ActionContextInput): ActionContext;
export declare function buildNextSteps(input: ChangeNextStepsInput): string[];
//# sourceMappingURL=change-status-policy.d.ts.map