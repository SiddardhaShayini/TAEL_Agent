"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.OllamaClient = void 0;
const http = __importStar(require("http"));
const https = __importStar(require("https"));
const url_1 = require("url");
class OllamaClient {
    baseUrl;
    modelName;
    numCtx;
    constructor(baseUrl = 'http://127.0.0.1:11434', modelName = 'tael-agent', numCtx = 4096) {
        this.baseUrl = baseUrl.replace(/\/+$/, '');
        this.modelName = modelName;
        this.numCtx = numCtx;
    }
    updateConfig(baseUrl, modelName, numCtx) {
        this.baseUrl = baseUrl.replace(/\/+$/, '');
        this.modelName = modelName;
        this.numCtx = numCtx;
    }
    getModelName() {
        return this.modelName;
    }
    getBaseUrl() {
        return this.baseUrl;
    }
    /**
     * Checks whether the local Ollama daemon is online and whether `tael-agent` is registered.
     */
    async checkStatus() {
        try {
            const raw = await this.httpRequest('GET', '/api/tags', undefined, 5000);
            const parsed = JSON.parse(raw);
            const models = Array.isArray(parsed.models)
                ? parsed.models.map((m) => m.name || '')
                : [];
            const targetBase = this.modelName.split(':')[0].toLowerCase();
            const modelAvailable = models.some((m) => m.toLowerCase() === this.modelName.toLowerCase() || m.toLowerCase().startsWith(targetBase + ':'));
            return {
                online: true,
                modelAvailable,
                installedModels: models,
                activeModel: this.modelName,
                baseUrl: this.baseUrl,
            };
        }
        catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            return {
                online: false,
                modelAvailable: false,
                installedModels: [],
                activeModel: this.modelName,
                baseUrl: this.baseUrl,
                error: msg,
            };
        }
    }
    /**
     * Streams a multi-turn chat completion from the local Ollama `/api/chat` endpoint.
     */
    async chatStream(messages, options = {}, onToken, abortSignal) {
        const urlObj = new url_1.URL(`${this.baseUrl}/api/chat`);
        const isHttps = urlObj.protocol === 'https:';
        const transport = isHttps ? https : http;
        const payload = JSON.stringify({
            model: this.modelName,
            messages,
            stream: true,
            options: {
                num_ctx: options.num_ctx ?? this.numCtx,
                temperature: options.temperature ?? 0.2,
                top_p: options.top_p ?? 0.9,
                num_predict: options.num_predict ?? 1536,
                repeat_penalty: options.repeat_penalty ?? 1.05,
                stop: options.stop ?? ['<|im_end|>', '<|im_start|>', '<|end_of_text|>', '</tool_call>'],
            },
        });
        const startTime = Date.now();
        return new Promise((resolve, reject) => {
            const req = transport.request({
                hostname: urlObj.hostname,
                port: urlObj.port || (isHttps ? 443 : 80),
                path: urlObj.pathname,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(payload, 'utf8'),
                },
            }, (res) => {
                if (res.statusCode && (res.statusCode < 200 || res.statusCode >= 300)) {
                    let errBody = '';
                    res.on('data', (chunk) => (errBody += chunk.toString()));
                    res.on('end', () => {
                        reject(new Error(`Ollama HTTP ${res.statusCode}: ${errBody}`));
                    });
                    return;
                }
                let accumulated = '';
                let buffer = '';
                let evalCount = 0;
                let evalDurationNs = 0;
                res.on('data', (chunk) => {
                    if (abortSignal?.aborted) {
                        req.destroy();
                        return;
                    }
                    buffer += chunk.toString('utf8');
                    const lines = buffer.split('\n');
                    buffer = lines.pop() ?? '';
                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed) {
                            continue;
                        }
                        try {
                            const json = JSON.parse(trimmed);
                            if (json.message && typeof json.message.content === 'string') {
                                const token = json.message.content;
                                accumulated += token;
                                if (onToken) {
                                    onToken(token, accumulated);
                                }
                            }
                            if (json.done) {
                                evalCount = json.eval_count || Math.max(1, Math.ceil(accumulated.length / 4));
                                evalDurationNs = json.eval_duration || (Date.now() - startTime) * 1e6;
                            }
                        }
                        catch {
                            // Ignore partial JSON line
                        }
                    }
                });
                res.on('end', () => {
                    // Auto-close <tool_call> tag if stopped on `</tool_call>` stop sequence
                    if (accumulated.includes('<tool_call>') && !accumulated.includes('</tool_call>')) {
                        const closeTag = '\n</tool_call>';
                        accumulated += closeTag;
                        if (onToken) {
                            onToken(closeTag, accumulated);
                        }
                    }
                    const elapsedMs = Math.max(1, evalDurationNs > 0 ? evalDurationNs / 1e6 : Date.now() - startTime);
                    const tps = Number(((evalCount / elapsedMs) * 1000).toFixed(2));
                    resolve({
                        content: accumulated,
                        evalCount,
                        evalDurationMs: Math.round(elapsedMs),
                        tokensPerSec: tps,
                        model: this.modelName,
                    });
                });
                res.on('error', (err) => reject(err));
            });
            req.on('error', (err) => reject(err));
            req.write(payload);
            req.end();
        });
    }
    httpRequest(method, endpoint, body, timeoutMs = 10000) {
        const urlObj = new url_1.URL(`${this.baseUrl}${endpoint}`);
        const isHttps = urlObj.protocol === 'https:';
        const transport = isHttps ? https : http;
        return new Promise((resolve, reject) => {
            const req = transport.request({
                hostname: urlObj.hostname,
                port: urlObj.port || (isHttps ? 443 : 80),
                path: urlObj.pathname,
                method,
                timeout: timeoutMs,
                headers: body
                    ? {
                        'Content-Type': 'application/json',
                        'Content-Length': Buffer.byteLength(body, 'utf8'),
                    }
                    : {},
            }, (res) => {
                let data = '';
                res.on('data', (chunk) => (data += chunk.toString('utf8')));
                res.on('end', () => {
                    if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
                        resolve(data);
                    }
                    else {
                        reject(new Error(`HTTP ${res.statusCode}: ${data}`));
                    }
                });
            });
            req.on('timeout', () => {
                req.destroy();
                reject(new Error(`Request timed out after ${timeoutMs}ms`));
            });
            req.on('error', (err) => reject(err));
            if (body) {
                req.write(body);
            }
            req.end();
        });
    }
}
exports.OllamaClient = OllamaClient;
//# sourceMappingURL=ollamaClient.js.map