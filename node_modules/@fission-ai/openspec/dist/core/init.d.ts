/**
 * Init Command
 *
 * Sets up OpenSpec with Agent Skills and /opsx:* slash commands.
 * This is the unified setup command that replaces both the old init and experimental commands.
 */
type InitCommandOptions = {
    tools?: string;
    force?: boolean;
    interactive?: boolean;
    profile?: string;
};
export declare class InitCommand {
    private readonly toolsArg?;
    private readonly force;
    private readonly interactiveOption?;
    private readonly profileOverride?;
    constructor(options?: InitCommandOptions);
    execute(targetPath: string): Promise<void>;
    private validate;
    private canPromptInteractively;
    private resolveProfileOverride;
    private handleLegacyCleanup;
    private performLegacyCleanup;
    private getSelectedTools;
    private resolveToolsArg;
    private validateTools;
    private createDirectoryStructure;
    private generateSkillsAndCommands;
    private createConfig;
    private displaySuccessMessage;
    private startSpinner;
    private removeSkillDirs;
    private removeCommandFiles;
}
export {};
//# sourceMappingURL=init.d.ts.map