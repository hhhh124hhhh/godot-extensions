/**
 * 主权上下文：由 sovereign index.ts 在 registerTools 时注入，
 * 提供 Godot 路径、脚本路径、image-gen key、工程路径。
 */
export interface SovereignCtx {
    godotPath: string | null;
    scriptPath: string;
    volcArkApiKey: string;
    godotProjectPath: string;
}
export interface McpTextResult {
    content: Array<{
        type: 'text';
        text: string;
    }>;
    isError?: boolean;
}
export declare const CS_UNIQUE_TOOLS: ({
    name: string;
    description: string;
    inputSchema: {
        type: string;
        properties: {
            action: {
                type: string;
                enum: string[];
                description: string;
            };
            directory: {
                type: string;
                description: string;
            };
            recursive: {
                type: string;
                description: string;
            };
            project_path?: undefined;
            scene_path?: undefined;
            output_path?: undefined;
            file_path?: undefined;
        };
        required: string[];
    };
} | {
    name: string;
    description: string;
    inputSchema: {
        type: string;
        properties: {
            project_path: {
                type: string;
                description: string;
            };
            scene_path: {
                type: string;
                description: string;
            };
            output_path: {
                type: string;
                description: string;
            };
            action?: undefined;
            directory?: undefined;
            recursive?: undefined;
            file_path?: undefined;
        };
        required: string[];
    };
} | {
    name: string;
    description: string;
    inputSchema: {
        type: string;
        properties: {
            project_path: {
                type: string;
                description: string;
            };
            file_path: {
                type: string;
                description: string;
            };
            action?: undefined;
            directory?: undefined;
            recursive?: undefined;
            scene_path?: undefined;
            output_path?: undefined;
        };
        required: string[];
    };
} | {
    name: string;
    description: string;
    inputSchema: {
        type: string;
        properties: {
            project_path: {
                type: string;
                description: string;
            };
            action?: undefined;
            directory?: undefined;
            recursive?: undefined;
            scene_path?: undefined;
            output_path?: undefined;
            file_path?: undefined;
        };
        required: string[];
    };
})[];
export declare function dispatchCsUnique(name: string, args: Record<string, unknown>, ctx: SovereignCtx): Promise<McpTextResult>;
//# sourceMappingURL=tools.d.ts.map