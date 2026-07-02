import { ValidationReport } from './types.js';
export declare class Validator {
    private strictMode;
    constructor(strictMode?: boolean);
    validateSpec(filePath: string): Promise<ValidationReport>;
    /**
     * Validate spec content from a string (used for pre-write validation of rebuilt specs)
     */
    validateSpecContent(specName: string, content: string): Promise<ValidationReport>;
    validateChange(filePath: string): Promise<ValidationReport>;
    /**
     * Validate delta-formatted spec files under a change directory.
     * Enforces:
     * - At least one delta across all files
     * - ADDED/MODIFIED: each requirement has SHALL/MUST and at least one scenario
     * - REMOVED: names only; no scenario/description required
     * - RENAMED: pairs well-formed
     * - No duplicates within sections; no cross-section conflicts per spec
     */
    validateChangeDeltaSpecs(changeDir: string): Promise<ValidationReport>;
    private convertZodErrors;
    private applySpecRules;
    private applyChangeRules;
    private enrichTopLevelError;
    private extractNameFromPath;
    private createReport;
    isValid(report: ValidationReport): boolean;
    private extractRequirementText;
    private containsShallOrMust;
    /**
     * Build an error message for a requirement block whose body lacks SHALL/MUST.
     *
     * When the SHALL/MUST keyword already appears in the requirement header (e.g.
     * `### Requirement: The system SHALL ...`) the original generic error
     * ("must contain SHALL or MUST") is confusing because the keyword is visibly
     * present in the spec. Per the OpenSpec conventions the keyword has to live
     * on the requirement body line (the line right after the header), so we point
     * the author at that exact fix when the keyword is found in the header only.
     */
    private buildMissingShallOrMustMessage;
    private countScenarios;
    private formatSectionList;
}
//# sourceMappingURL=validator.d.ts.map