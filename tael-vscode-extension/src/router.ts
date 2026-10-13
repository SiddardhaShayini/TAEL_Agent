/**
 * TAEL V2: Dynamic Task Router for VS Code Extension
 * Classifies user prompts into 9 software engineering categories with confidence scoring,
 * tailored system prompts, tool sets, and generation hyperparameters.
 */

export type TaskCategory =
  | 'Programming'
  | 'Debugging'
  | 'Refactoring'
  | 'SQL'
  | 'Architecture'
  | 'Git'
  | 'Tool Use'
  | 'Math'
  | 'General Chat';

export interface RouteDecision {
  category: TaskCategory;
  confidence: number;
  isFallback: boolean;
  temperature: number;
  topP: number;
  maxTokens: number;
  allowedTools: string[];
  systemPrompt: string;
}

interface CategoryRule {
  category: TaskCategory;
  temperature: number;
  topP: number;
  maxTokens: number;
  patterns: RegExp[];
  primaryKeywords: string[];
  secondaryKeywords: string[];
  allowedTools: string[];
  systemDirective: string;
}

const ALL_TOOLS = [
  'read_file',
  'write_file',
  'list_dir',
  'search_text',
  'git_status',
  'git_diff',
  'git_log',
  'git_branch',
  'execute_python',
  'execute_terminal_command',
];

const CATEGORY_RULES: CategoryRule[] = [
  {
    category: 'SQL',
    temperature: 0.1,
    topP: 0.85,
    maxTokens: 1024,
    patterns: [
      /\bSELECT\b[\s\S]+\bFROM\b/i,
      /\b(INNER|LEFT|RIGHT|FULL)\s+JOIN\b/i,
      /\bGROUP\s+BY\b|\bORDER\s+BY\b|\bHAVING\b/i,
      /\bCREATE\s+TABLE\b|\bALTER\s+TABLE\b/i,
    ],
    primaryKeywords: ['sql', 'sqlite', 'postgres', 'postgresql', 'mysql', 'query', 'subquery', 'cte', 'schema'],
    secondaryKeywords: ['table', 'join', 'index', 'foreign key', 'primary key', 'aggregate'],
    allowedTools: ['read_file', 'search_text', 'execute_python'],
    systemDirective:
      'You are TAEL operating in SQL & Database Engineering mode. Write clean, standards-compliant SQL queries with explicit JOINs, CTEs, and proper indexing strategies.',
  },
  {
    category: 'Git',
    temperature: 0.1,
    topP: 0.85,
    maxTokens: 1024,
    patterns: [
      /\bgit\s+(commit|push|pull|rebase|merge|cherry-pick|stash|reset|checkout|branch|log|diff|status|bisect)\b/i,
      /\bsquash\s+commits?\b|\binteractive\s+rebase\b/i,
    ],
    primaryKeywords: ['git', 'rebase', 'cherry-pick', 'merge conflict', 'commit', 'branch', 'stash', 'HEAD'],
    secondaryKeywords: ['repository', 'pull request', 'diff', 'history', 'origin', 'remote'],
    allowedTools: ['git_status', 'git_diff', 'git_log', 'git_branch', 'read_file'],
    systemDirective:
      'You are TAEL operating in Git Version Control mode. Provide safe, exact Git commands and inspect repository status using Git tools when needed.',
  },
  {
    category: 'Tool Use',
    temperature: 0.15,
    topP: 0.9,
    maxTokens: 2048,
    patterns: [
      /\b(create|write|save|update|modify)\s+(a\s+)?(file|folder|directory|script|project)\b/i,
      /\b(run|execute)\s+(the\s+)?(command|script|test|terminal|python)\b/i,
      /\b<tool_call>\b/i,
      /\b(search|list|read)\s+(files?|directory|workspace|codebase)\b/i,
    ],
    primaryKeywords: ['write_file', 'read_file', 'list_dir', 'search_text', 'execute_python', 'execute_terminal_command', 'tool_call'],
    secondaryKeywords: ['create file', 'in folder', 'run script', 'list files', 'autonomous', 'tool'],
    allowedTools: ALL_TOOLS,
    systemDirective:
      'You are TAEL operating in Autonomous Tool Execution mode. When performing workspace actions (reading/writing files, searching, running commands), emit a valid <tool_call>{"name": "...", "arguments": {...}}</tool_call> block and wait for <tool_response>.',
  },
  {
    category: 'Debugging',
    temperature: 0.2,
    topP: 0.9,
    maxTokens: 2048,
    patterns: [
      /Traceback \(most recent call last\)/i,
      /\b(TypeError|ValueError|KeyError|IndexError|AttributeError|SyntaxError|ReferenceError|NullPointerException)\b/,
      /\b(fix|debug|resolve|diagnose)\s+(this\s+)?(bug|error|exception|crash|issue|problem)\b/i,
    ],
    primaryKeywords: ['debug', 'bug', 'traceback', 'exception', 'stack trace', 'segfault', 'crash', 'failing'],
    secondaryKeywords: ['error', 'fix', 'issue', 'broken', 'undefined', 'null', 'diagnostic'],
    allowedTools: ['read_file', 'write_file', 'search_text', 'execute_python', 'git_diff'],
    systemDirective:
      'You are TAEL operating in Debugging & Root-Cause Analysis mode. Identify the exact root cause of errors or diagnostics, explain why it happens, and provide the minimal, verified code fix.',
  },
  {
    category: 'Refactoring',
    temperature: 0.2,
    topP: 0.9,
    maxTokens: 2048,
    patterns: [
      /\brefactor\b/i,
      /\bguard\s+clauses?\b|\bearly\s+returns?\b/i,
      /\bclean\s+up\b|\bmodularize\b|\bdecouple\b|\bsimplify\b/i,
    ],
    primaryKeywords: ['refactor', 'refactoring', 'clean code', 'code smell', 'guard clause', 'dry', 'solid'],
    secondaryKeywords: ['readable', 'maintainable', 'simplify', 'extract', 'optimize', 'restructure'],
    allowedTools: ['read_file', 'write_file', 'search_text'],
    systemDirective:
      'You are TAEL operating in Code Refactoring mode. Improve readability, reduce cyclomatic complexity, apply guard clauses and SOLID principles, and strictly preserve external behavior.',
  },
  {
    category: 'Architecture',
    temperature: 0.35,
    topP: 0.92,
    maxTokens: 2048,
    patterns: [
      /\bsystem\s+design\b|\bmicroservices?\b|\bevent[- ]driven\b/i,
      /\bhigh\s+availability\b|\bload\s+balanc(er|ing)\b|\bmessage\s+queue\b/i,
      /\bdesign\s+a\s+(scalable|distributed)\b/i,
    ],
    primaryKeywords: ['architecture', 'microservice', 'kafka', 'redis', 'scalability', 'throughput', 'distributed', 'system design'],
    secondaryKeywords: ['pattern', 'idempotency', 'sharding', 'caching', 'backpressure', 'latency', 'gateway'],
    allowedTools: ['read_file', 'list_dir', 'search_text'],
    systemDirective:
      'You are TAEL operating in Software Architecture & System Design mode. Structure solutions with clear component boundaries, data flow, fault tolerance, scalability, and trade-offs.',
  },
  {
    category: 'Math',
    temperature: 0.0,
    topP: 0.8,
    maxTokens: 1536,
    patterns: [
      /\b(calculate|compute|solve|prove|integrate|differentiate)\b[\s\S]*(\d+|equation|matrix|probability|integral|derivative)/i,
      /\bO\([n1log\s*^23]+\)\b/,
    ],
    primaryKeywords: ['theorem', 'calculus', 'eigenvalue', 'probability', 'combinatorics', 'derivative', 'integral', 'equation'],
    secondaryKeywords: ['math', 'formula', 'prime', 'factorial', 'fibonacci', 'modulo', 'complexity'],
    allowedTools: ['execute_python'],
    systemDirective:
      'You are TAEL operating in Mathematical & Algorithmic Reasoning mode. Show rigorous step-by-step derivations and verify numerical results.',
  },
  {
    category: 'Programming',
    temperature: 0.15,
    topP: 0.9,
    maxTokens: 2048,
    patterns: [
      /\b(write|implement|create|generate|build)\s+(a\s+)?(python|typescript|javascript|rust|go|java|c\+\+|html|css)?\s*(function|class|method|module|component|algorithm|api)\b/i,
      /```[a-zA-Z]*\n[\s\S]+```/,
      /\bdef\s+\w+\s*\(|\bfunction\s+\w+\s*\(|\bclass\s+\w+/,
    ],
    primaryKeywords: ['function', 'class', 'implement', 'algorithm', 'python', 'typescript', 'javascript', 'code', 'async', 'interface'],
    secondaryKeywords: ['array', 'string', 'hashmap', 'dictionary', 'loop', 'return', 'type', 'export'],
    allowedTools: ['read_file', 'write_file', 'search_text', 'execute_python'],
    systemDirective:
      'You are TAEL operating in Software Engineering & Code Generation mode. Write production-ready, well-typed, idiomatic code with clear edge-case handling.',
  },
];

export class TaskRouter {
  public route(prompt: string, forceToolMode: boolean = false): RouteDecision {
    const clean = (prompt || '').trim();
    const lower = clean.toLowerCase();

    if (forceToolMode) {
      const toolRule = CATEGORY_RULES.find((r) => r.category === 'Tool Use')!;
      return {
        category: 'Tool Use',
        confidence: 0.98,
        isFallback: false,
        temperature: toolRule.temperature,
        topP: toolRule.topP,
        maxTokens: toolRule.maxTokens,
        allowedTools: ALL_TOOLS,
        systemPrompt: this.buildSystemPrompt(toolRule.systemDirective, ALL_TOOLS, true),
      };
    }

    const scores: Map<TaskCategory, number> = new Map();

    for (const rule of CATEGORY_RULES) {
      let score = 0;
      for (const regex of rule.patterns) {
        if (regex.test(clean)) {
          score += 5.0;
        }
      }
      for (const kw of rule.primaryKeywords) {
        if (lower.includes(kw.toLowerCase())) {
          score += 3.0;
        }
      }
      for (const kw of rule.secondaryKeywords) {
        if (lower.includes(kw.toLowerCase())) {
          score += 1.5;
        }
      }
      scores.set(rule.category, score);
    }

    let bestCategory: TaskCategory = 'General Chat';
    let bestScore = 0;

    for (const [cat, sc] of scores.entries()) {
      if (sc > bestScore) {
        bestScore = sc;
        bestCategory = cat;
      }
    }

    // Confidence calibration
    if (bestScore < 2.5) {
      return {
        category: 'General Chat',
        confidence: bestScore === 0 ? 0.85 : 0.55,
        isFallback: bestScore > 0,
        temperature: 0.6,
        topP: 0.92,
        maxTokens: 1024,
        allowedTools: ['read_file', 'list_dir', 'search_text'],
        systemPrompt: this.buildSystemPrompt(
          'You are TAEL, a specialized autonomous software engineering and coding AI assistant running locally via Ollama.',
          ['read_file', 'list_dir', 'search_text'],
          false
        ),
      };
    }

    const confidence = Number(Math.min(0.99, 0.55 + Math.tanh(bestScore / 10.0) * 0.44).toFixed(2));
    const matchedRule = CATEGORY_RULES.find((r) => r.category === bestCategory)!;
    const includeToolFormat = bestCategory === 'Tool Use';

    return {
      category: bestCategory,
      confidence,
      isFallback: false,
      temperature: matchedRule.temperature,
      topP: matchedRule.topP,
      maxTokens: matchedRule.maxTokens,
      allowedTools: matchedRule.allowedTools,
      systemPrompt: this.buildSystemPrompt(
        matchedRule.systemDirective,
        matchedRule.allowedTools,
        includeToolFormat
      ),
    };
  }

  private buildSystemPrompt(directive: string, allowedTools: string[], includeFullToolSpec: boolean): string {
    if (!includeFullToolSpec) {
      return `${directive}\nWhen providing code changes, wrap code in fenced markdown blocks with the language identifier.`;
    }

    return `${directive}

Available Sandboxed Workspace Tools:
- read_file: {"path": "relative/path", "start_line": 1, "end_line": 200}
- write_file: {"path": "relative/path", "content": "..."}
- list_dir: {"path": "."}
- search_text: {"query": "pattern", "path": "."}
- git_status: {}
- git_diff: {"staged": false}
- git_log: {"max_count": 5}
- git_branch: {}
- execute_python: {"code": "print(1+1)"}
- execute_terminal_command: {"command": "pytest"}

To invoke a tool, output ONLY a valid XML <tool_call> tag containing JSON:
<tool_call>
{"name": "write_file", "arguments": {"path": "example.py", "content": "print('Hello')"}}
</tool_call>`;
  }
}
