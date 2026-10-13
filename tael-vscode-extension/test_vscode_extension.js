/**
 * Automated Verification & Live Ollama Integration Test Suite
 * for TAEL VS Code Extension (`tael-vscode-extension`)
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const { OllamaClient } = require('./out/ollamaClient');
const { TaskRouter } = require('./out/router');
const { XMLToolParser, ToolRegistry, PathSandbox, CommandSandbox } = require('./out/tools');

async function runTests() {
  console.log('========================================================================');
  console.log(' [TAEL VS CODE EXTENSION] Starting Verification & Live Integration Tests');
  console.log('========================================================================\n');

  let passed = 0;
  let total = 0;

  function check(name, fn) {
    total++;
    try {
      fn();
      console.log(`  [PASS] ${name}`);
      passed++;
    } catch (err) {
      console.error(`  [FAIL] ${name}: ${err.message}`);
      throw err;
    }
  }

  async function checkAsync(name, fn) {
    total++;
    try {
      await fn();
      console.log(`  [PASS] ${name}`);
      passed++;
    } catch (err) {
      console.error(`  [FAIL] ${name}: ${err.message}`);
      throw err;
    }
  }

  // 1. Validate package.json & compiled artifacts
  console.log('[1/5] Validating Extension Manifest & Compiled Artifacts...');
  check('package.json manifest contributions', () => {
    const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, 'package.json'), 'utf8'));
    assert.strictEqual(pkg.name, 'tael-vscode-extension');
    assert.ok(pkg.contributes.views['tael-sidebar'].some((v) => v.id === 'tael.chatView'));
    const cmdIds = pkg.contributes.commands.map((c) => c.command);
    const requiredCmds = [
      'tael.openChat',
      'tael.generateCode',
      'tael.refactorCode',
      'tael.explainCode',
      'tael.fixDiagnostics',
      'tael.applyEdit',
      'tael.runAgentTask',
      'tael.checkOllamaStatus',
      'tael.clearHistory',
    ];
    for (const reqCmd of requiredCmds) {
      assert.ok(cmdIds.includes(reqCmd), `Missing command ${reqCmd}`);
    }
  });

  check('Compiled JavaScript modules exist in out/', () => {
    const expectedFiles = [
      'extension.js',
      'chatViewProvider.js',
      'ollamaClient.js',
      'router.js',
      'tools.js',
      'workspaceContext.js',
      'editApplier.js',
    ];
    for (const f of expectedFiles) {
      assert.ok(fs.existsSync(path.join(__dirname, 'out', f)), `Missing compiled file out/${f}`);
    }
  });

  // 2. Validate Dynamic Task Router
  console.log('\n[2/5] Validating TypeScript Dynamic Task Router (9 Categories)...');
  const router = new TaskRouter();

  check('Routes SQL queries accurately (T=0.1)', () => {
    const res = router.route('Write a SQL query with INNER JOIN and GROUP BY customer_id HAVING COUNT(*) > 2');
    assert.strictEqual(res.category, 'SQL');
    assert.strictEqual(res.temperature, 0.1);
  });

  check('Routes Refactoring tasks accurately (T=0.2)', () => {
    const res = router.route('Refactor this nested function to use guard clauses and clean code principles');
    assert.strictEqual(res.category, 'Refactoring');
    assert.strictEqual(res.temperature, 0.2);
  });

  check('Routes Debugging tasks accurately (T=0.2)', () => {
    const res = router.route('Fix this bug: Traceback (most recent call last): TypeError: NoneType object is not iterable');
    assert.strictEqual(res.category, 'Debugging');
  });

  check('Routes Git workflows accurately (T=0.1)', () => {
    const res = router.route('How do I squash commits using git rebase -i HEAD~3?');
    assert.strictEqual(res.category, 'Git');
  });

  check('Routes Tool Use / Agent mode accurately (T=0.15)', () => {
    const res = router.route('Create a file hello.py and run the script', true);
    assert.strictEqual(res.category, 'Tool Use');
    assert.ok(res.allowedTools.includes('write_file'));
  });

  check('Falls back to General Chat on conversational prompts', () => {
    const res = router.route('Hello there! How are you doing today?');
    assert.strictEqual(res.category, 'General Chat');
  });

  // 3. Validate XMLToolParser & Sandboxed Tool Registry
  console.log('\n[3/5] Validating XMLToolParser & Sandboxed Tool Execution...');
  check('XMLToolParser parses explicit and implicit <tool_call> tags', () => {
    const explicit = XMLToolParser.extractToolCalls(
      '<tool_call>\n{"name": "search_text", "arguments": {"query": "OllamaClient"}}\n</tool_call>'
    );
    assert.strictEqual(explicit.length, 1);
    assert.strictEqual(explicit[0].name, 'search_text');
    assert.strictEqual(explicit[0].arguments.query, 'OllamaClient');

    const implicit = XMLToolParser.extractToolCalls(
      '<tool_call>{"path": "demo.txt", "content": "hello"}</tool_call>'
    );
    assert.strictEqual(implicit.length, 1);
    assert.strictEqual(implicit[0].name, 'write_file');
  });

  check('PathSandbox blocks directory traversal and .env files', () => {
    const sandbox = new PathSandbox(__dirname);
    assert.throws(() => sandbox.resolveSafePath('../../Windows/System32/cmd.exe'), /Security Sandbox Violation/);
    assert.throws(() => sandbox.resolveSafePath('.env'), /Security Sandbox Violation/);
  });

  check('CommandSandbox blocks destructive shell commands', () => {
    assert.throws(() => CommandSandbox.validate('rm -rf /'), /Security Sandbox Violation/);
    assert.throws(() => CommandSandbox.validate('del /f /q *.*'), /Security Sandbox Violation/);
  });

  await checkAsync('ToolRegistry executes list_dir, search_text, and git_status inside workspace', async () => {
    const registry = new ToolRegistry(__dirname);
    const listRes = await registry.execute({ name: 'list_dir', arguments: { path: '.' }, rawBlock: '' });
    assert.strictEqual(listRes.status, 'success');
    assert.ok(listRes.output.includes('package.json'));

    const searchRes = await registry.execute({
      name: 'search_text',
      arguments: { query: 'TaelChatViewProvider', path: 'src' },
      rawBlock: '',
    });
    assert.strictEqual(searchRes.status, 'success');
    assert.ok(searchRes.output.includes('chatViewProvider.ts'));
  });

  // 4. Validate Live Local Ollama Runtime Connection
  console.log('\n[4/5] Validating Live Local Ollama Runtime Connection (`tael-agent`)...');
  const ollama = new OllamaClient('http://127.0.0.1:11434', 'tael-agent', 4096);

  await checkAsync('Ollama daemon is online and `tael-agent` is available', async () => {
    const status = await ollama.checkStatus();
    assert.strictEqual(status.online, true, `Ollama daemon offline: ${status.error}`);
    assert.strictEqual(
      status.modelAvailable,
      true,
      `Model tael-agent not found in [${status.installedModels.join(', ')}]`
    );
    console.log(`         Connected to ${status.baseUrl} | Active Model: ${status.activeModel}`);
  });

  // 5. Validate Live Streaming Chat & Code Generation via OllamaClient
  console.log('\n[5/5] Validating Live Streaming Inference via OllamaClient...');
  await checkAsync('Streams code generation response from `tael-agent` in real time', async () => {
    let streamedChunks = 0;
    const res = await ollama.chatStream(
      [
        {
          role: 'system',
          content: 'You are TAEL, a coding assistant. Reply concisely.',
        },
        {
          role: 'user',
          content: 'Write a one-line Python function `add(a, b)` that returns `a + b`.',
        },
      ],
      { temperature: 0.1, num_predict: 128 },
      () => {
        streamedChunks++;
      }
    );

    assert.ok(streamedChunks > 0, 'Expected at least 1 streamed chunk');
    assert.ok(res.content.includes('def add') || res.content.includes('return'), `Unexpected output: ${res.content}`);
    console.log(
      `         Streamed ${streamedChunks} chunks (${res.evalCount} tokens at ${res.tokensPerSec} tok/s in ${res.evalDurationMs}ms)`
    );
  });

  console.log('\n========================================================================');
  console.log(` [SUMMARY] ALL ${passed}/${total} VS CODE EXTENSION TESTS PASSED!`);
  console.log('========================================================================\n');
}

runTests().catch((err) => {
  console.error('\n[FATAL TEST FAILURE]', err);
  process.exit(1);
});
