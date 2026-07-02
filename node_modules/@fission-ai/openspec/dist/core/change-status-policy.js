export function summarizePlanningHome(planningHome) {
    if (!planningHome) {
        return undefined;
    }
    return {
        kind: planningHome.kind,
        root: planningHome.root,
        changesDir: planningHome.changesDir,
        defaultSchema: planningHome.defaultSchema,
    };
}
export function buildActionContext(input) {
    return {
        mode: 'repo-local',
        sourceOfTruth: 'repo',
        planningArtifacts: input.artifactIds,
        linkedContext: [],
        allowedEditRoots: [input.projectRoot],
        requiresAffectedAreaSelection: false,
        constraints: ['Repo-local change artifacts and implementation edits are scoped to this project.'],
    };
}
export function buildNextSteps(input) {
    const readyArtifact = input.artifactStatuses.find((artifact) => artifact.status === 'ready');
    const steps = [];
    if (readyArtifact) {
        const storeFlag = input.storeId ? ` --store ${input.storeId}` : '';
        steps.push(`Run openspec instructions ${readyArtifact.id} --change "${input.changeName}"${storeFlag} --json before writing that artifact.`);
    }
    else if (input.allArtifactsComplete) {
        steps.push('All planning artifacts are complete; review tasks before implementation.');
    }
    return steps;
}
//# sourceMappingURL=change-status-policy.js.map