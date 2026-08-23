export interface RunGodotOpResult {
    stdout: string;
    stderr: string;
}
/**
 * 运行 bundled godot_operations.gd 的某一 operation。
 * @param godotPath 检测到的 Godot 可执行文件路径（无则报错）
 * @param scriptPath godot_operations.gd 的绝对路径
 * @param projectPath 工程目录（--path，res:// 基准）
 * @param operation .gd 中 match 的分支名
 * @param params 已转 snake_case 的参数对象（会被 JSON.stringify 成命令行参数）
 */
export declare function runGodotOp(godotPath: string | null, scriptPath: string, projectPath: string, operation: string, params: Record<string, unknown>): Promise<RunGodotOpResult>;
//# sourceMappingURL=run-godot-op.d.ts.map