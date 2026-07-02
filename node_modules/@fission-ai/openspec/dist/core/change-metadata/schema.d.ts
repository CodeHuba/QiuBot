import { z } from 'zod';
export { isKebabId } from '../id.js';
export declare const InitiativeLinkSchema: z.ZodObject<{
    store: z.ZodString;
    id: z.ZodString;
}, z.core.$strict>;
export type InitiativeLink = z.infer<typeof InitiativeLinkSchema>;
export declare const ChangeMetadataSchema: z.ZodObject<{
    schema: z.ZodString;
    created: z.ZodOptional<z.ZodString>;
    goal: z.ZodOptional<z.ZodString>;
    affected_areas: z.ZodOptional<z.ZodArray<z.ZodString>>;
    initiative: z.ZodOptional<z.ZodObject<{
        store: z.ZodString;
        id: z.ZodString;
    }, z.core.$strict>>;
}, z.core.$strip>;
export type ChangeMetadata = z.infer<typeof ChangeMetadataSchema>;
//# sourceMappingURL=schema.d.ts.map