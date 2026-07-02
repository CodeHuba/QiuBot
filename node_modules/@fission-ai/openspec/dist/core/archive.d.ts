export interface ArchiveOptions {
    yes?: boolean;
    skipSpecs?: boolean;
    noValidate?: boolean;
    validate?: boolean;
    json?: boolean;
    store?: string;
    storePath?: string;
}
export declare class ArchiveCommand {
    execute(changeName?: string, options?: ArchiveOptions): Promise<void>;
    private printJsonFailure;
    /**
     * Shared archive flow. In human mode (json=false) prompts and prose match
     * the historical behavior and cancellations return null. In JSON mode no
     * prose reaches stdout and every blocked path throws.
     */
    private run;
    private selectChange;
    private getArchiveDate;
}
//# sourceMappingURL=archive.d.ts.map