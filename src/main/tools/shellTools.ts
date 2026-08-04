import { spawn } from 'child_process'

const DEFAULT_TIMEOUT_MS = 60_000
const MAX_OUTPUT_CHARS = 30_000

export interface CommandResult {
  exitCode: number | null
  output: string
  timedOut: boolean
}

/**
 * Run a shell command with the project directory as cwd. Output is captured
 * (stdout + stderr interleaved) and truncated to a safe size. A timeout
 * guards against hanging processes.
 */
export function runCommand(root: string, command: string, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<CommandResult> {
  return new Promise((resolvePromise) => {
    const shell = process.platform === 'win32' ? 'cmd' : 'bash'
    const shellFlag = process.platform === 'win32' ? '/c' : '-c'

    const child = spawn(shell, [shellFlag, command], {
      cwd: root,
      env: process.env,
      windowsHide: true
    })

    let output = ''
    let truncated = false
    let timedOut = false

    const append = (chunk: Buffer): void => {
      if (truncated) return
      output += chunk.toString('utf8')
      if (output.length > MAX_OUTPUT_CHARS) {
        output = output.slice(0, MAX_OUTPUT_CHARS) + '\n... [output truncated]'
        truncated = true
      }
    }

    child.stdout.on('data', append)
    child.stderr.on('data', append)

    const timer = setTimeout(() => {
      timedOut = true
      child.kill('SIGKILL')
    }, timeoutMs)

    child.on('error', (err) => {
      clearTimeout(timer)
      resolvePromise({ exitCode: null, output: `Failed to start command: ${err.message}`, timedOut })
    })

    child.on('close', (code) => {
      clearTimeout(timer)
      const suffix = timedOut ? `\n[command timed out after ${timeoutMs}ms]` : ''
      resolvePromise({ exitCode: code, output: (output || '(no output)') + suffix, timedOut })
    })
  })
}
